import logging
import socket
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

logger = logging.getLogger("compust.database")
settings = get_settings()


def _is_mysql_reachable(url: str) -> bool:
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

            with socket.create_connection((host, port), timeout=1.0):
                return True
    except Exception:
        return False
    return False


def create_resilient_engine():
    db_url = settings.database_url

    # Check if SQLite explicitly requested
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False})

    # Check if MySQL server is actively reachable
    if db_url.startswith("mysql"):
        if _is_mysql_reachable(db_url):
            try:
                eng = create_engine(db_url, pool_pre_ping=settings.db_pool_pre_ping)
                # Verify connection with ping
                with eng.connect() as conn:
                    pass
                logger.info(f"Connected to MySQL database at {db_url.split('@')[-1]}")
                return eng
            except Exception as e:
                logger.warning(f"MySQL connection failed ({e}). Falling back to local standalone SQLite.")
        else:
            logger.info("MySQL service is not reachable. Activating standalone SQLite database.")

    # Standalone fallback: embedded local SQLite database for non-technical Windows release
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = data_dir / "compust_local.db"
    sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"

    logger.info(f"Initialized standalone SQLite database at: {sqlite_path}")
    return create_engine(sqlite_url, connect_args={"check_same_thread": False})


engine = create_resilient_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_database_schema():
    """Initializes all database tables from declarative models if they do not exist."""
    try:
        from .models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema verified and initialized.")
    except Exception as exc:
        logger.error(f"Error initializing database schema: {exc}")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
