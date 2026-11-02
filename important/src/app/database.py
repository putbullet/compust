import logging
import os
import socket
from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .paths import get_app_mode, get_database_path

logger = logging.getLogger("compust.database")
settings = get_settings()

_ACTIVE_CONFIG_FALLBACK_ACTIVE = False


def _is_mysql_reachable(url: str, retries: int = 2, timeout: float = 2.0) -> bool:
    """Quick pre-flight TCP check if the configured database host/port is accepting connections."""
    try:
        if "@" in url:
            host_port = url.split("@", 1)[1].split("/", 1)[0]
            host = "127.0.0.1"
            port = 3306
            if ":" in host_port:
                h, p = host_port.split(":", 1)
                if h:
                    host = h
                if p.isdigit():
                    port = int(p)
            elif host_port:
                host = host_port

            for _ in range(retries):
                try:
                    with socket.create_connection((host, port), timeout=timeout):
                        return True
                except Exception:
                    pass
    except Exception:
        return False
    return False


def get_default_sqlite_url() -> str:
    sqlite_path = get_database_path()
    return f"sqlite:///{sqlite_path.as_posix()}"


def create_resilient_engine() -> Any:
    r"""
    Constructs the database engine according to strict precedence rules:
    1. Explicit user configuration in db_config.json (if enabled)
    2. (Dev mode only) COMPUST_DATABASE_URL / .env and auto-probe
    3. (Installed mode default) Standalone SQLite at %LOCALAPPDATA%\Compust\data\compust.db
    """
    global _ACTIVE_CONFIG_FALLBACK_ACTIVE
    _ACTIVE_CONFIG_FALLBACK_ACTIVE = False

    try:
        from .services.db_config import get_active_db_connection_params
        cfg = get_active_db_connection_params()
        if cfg and cfg.get("source") == "config_file" and cfg.get("engine") == "mysql":
            user = cfg.get("user") or "root"
            pwd = cfg.get("password") or ""
            host = cfg.get("host") or "127.0.0.1"
            port = cfg.get("port") or 3306
            db_name = cfg.get("database") or "compust"
            url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db_name}"

            if _is_mysql_reachable(url):
                try:
                    eng = create_engine(url, pool_pre_ping=settings.db_pool_pre_ping)
                    with eng.connect():
                        pass
                    logger.info(f"Connected to user-configured MySQL database at {host}:{port}/{db_name}")
                    return eng
                except Exception as exc:
                    logger.warning(
                        f"Configured MySQL at {host}:{port}/{db_name} connection failed ({exc}). "
                        f"Activating emergency fallback to local standalone SQLite."
                    )
                    _ACTIVE_CONFIG_FALLBACK_ACTIVE = True
            else:
                logger.warning(
                    f"Configured MySQL at {host}:{port}/{db_name} is unreachable. "
                    f"Activating emergency fallback to local standalone SQLite."
                )
                _ACTIVE_CONFIG_FALLBACK_ACTIVE = True
    except Exception as cfg_err:
        logger.debug(f"Note checking db_config.json: {cfg_err}")

    mode = get_app_mode()
    # In dev mode, check settings.database_url / env if not explicitly configured
    if mode == "dev":
        db_url = settings.database_url
        if db_url.startswith("mysql") and _is_mysql_reachable(db_url):
            try:
                eng = create_engine(db_url, pool_pre_ping=settings.db_pool_pre_ping)
                with eng.connect():
                    pass
                logger.info(f"Connected to dev MySQL database at {db_url.split('@')[-1]}")
                return eng
            except Exception as e:
                logger.warning(f"Dev MySQL connection failed ({e}). Falling back to local standalone SQLite.")

    # Default standalone SQLite database
    sqlite_url = get_default_sqlite_url()
    logger.info(f"Initialized standalone SQLite database engine: {sqlite_url}")
    return create_engine(sqlite_url, connect_args={"check_same_thread": False})


engine = create_resilient_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def rebind_database_engine(new_engine: Any) -> None:
    """Rebinds global engine and SessionLocal to a newly created engine."""
    global engine, SessionLocal
    try:
        engine.dispose()
    except Exception:
        pass
    engine = new_engine
    SessionLocal.configure(bind=engine)
    logger.info(f"Global database engine rebound to: {engine.dialect.name} ({engine.url})")


def switch_active_database(
    target_engine: str,
    params: dict[str, Any] | None = None,
    run_migrations: bool = True,
) -> dict[str, Any]:
    """
    Switches active database connection between MySQL and SQLite live.
    Updates db_config.json and rebinds global engine.
    """
    from .services.db_config import save_db_config, clear_db_config

    old_engine = engine
    target_engine = target_engine.lower()

    if target_engine == "mysql":
        if not params:
            raise ValueError("MySQL connection parameters are required.")
        host = params.get("host", "127.0.0.1")
        port = int(params.get("port", 3306))
        user = params.get("user", "root")
        pwd = params.get("password", "")
        db_name = params.get("database", "compust")

        url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db_name}"
        if not _is_mysql_reachable(url):
            raise ConnectionError(f"MySQL server at {host}:{port} is not reachable.")

        new_eng = create_engine(url, pool_pre_ping=True)
        # Test connection
        with new_eng.connect():
            pass

        # Rebind
        rebind_database_engine(new_eng)

        # Run migrations if requested
        if run_migrations:
            init_database_schema()

        # Save config
        save_db_config("mysql", host=host, port=port, user=user, password=pwd, database=db_name, enabled=True)
        return get_active_database_info()

    elif target_engine == "sqlite":
        sqlite_url = get_default_sqlite_url()
        new_eng = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        with new_eng.connect():
            pass

        rebind_database_engine(new_eng)
        if run_migrations:
            init_database_schema()

        # Disable or clear MySQL config
        clear_db_config()
        return get_active_database_info()

    else:
        raise ValueError(f"Unsupported database engine: {target_engine}")


def get_active_database_info() -> dict[str, Any]:
    """Return comprehensive metadata on currently active database engine."""
    from .schema_reconciler import get_schema_diff

    dialect_name = engine.dialect.name
    url_str = str(engine.url)
    is_sqlite = dialect_name == "sqlite"

    if is_sqlite:
        raw_path = url_str.split("sqlite:///", 1)[1].split("?", 1)[0]
        p = Path(raw_path)
        location = str(p.resolve())
        size_bytes = p.stat().st_size if p.is_file() else 0
        size_mb = round(size_bytes / (1024 * 1024), 2)
    else:
        # Strip password from url string
        if "@" in url_str:
            pre, post = url_str.split("@", 1)
            prefix = pre.split("://", 1)[0]
            location = f"{prefix}://***:***@{post}"
        else:
            location = url_str
        size_mb = None

    table_counts: dict[str, int] = {}
    key_tables = ["users", "jobs", "companies", "user_applications", "contacts", "resumes"]
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.connect() as conn:
        for t in key_tables:
            if t in existing_tables:
                try:
                    table_counts[t] = conn.execute(text(f"SELECT count(*) FROM {t}")).scalar() or 0
                except Exception:
                    table_counts[t] = 0
            else:
                table_counts[t] = 0

    diff = get_schema_diff(engine)
    return {
        "engine": dialect_name,
        "location": location,
        "is_sqlite": is_sqlite,
        "size_mb": size_mb,
        "table_counts": table_counts,
        "schema_synced": diff["is_synced"],
        "missing_tables": diff["missing_tables"],
        "missing_columns": diff["missing_columns"],
        "is_fallback_active": _ACTIVE_CONFIG_FALLBACK_ACTIVE,
    }


def init_database_schema():
    """Initializes and self-heals all database tables from migrations and declarative models."""
    try:
        from .schema_reconciler import reconcile_database_schema
        result = reconcile_database_schema(engine=engine, auto_backup=True)
        if result.get("applied_migrations"):
            logger.info(f"Applied {len(result['applied_migrations'])} database migration(s): {', '.join(result['applied_migrations'])}")
        if result.get("added_columns"):
            logger.info(f"Auto-healed database columns: {result['added_columns']}")

        try:
            from .services.ai_gateway import sync_user_ai_config_on_startup
            sync_user_ai_config_on_startup()
        except Exception as seed_err:
            logger.debug(f"Initial AI config sync note: {seed_err}")

        logger.info(f"Database schema verified and initialized on {engine.dialect.name}.")
        return result
    except Exception as exc:
        logger.error(f"Error initializing database schema on {engine.dialect.name}: {exc}")
        raise


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
