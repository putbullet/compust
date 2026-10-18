import logging
import socket
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

logger = logging.getLogger("compust.database")
settings = get_settings()


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
    from .paths import get_database_path
    sqlite_path = get_database_path()
    sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"

    logger.info(f"Initialized standalone SQLite database at: {sqlite_path}")
    return create_engine(sqlite_url, connect_args={"check_same_thread": False})


engine = create_resilient_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_database_schema():
    """Initializes all database tables from declarative models if they do not exist."""
    try:
        from sqlalchemy import text
        from .models import Base
        from .models_mock_interview import (
            MockInterviewSession,
            MockInterviewTurn,
            MockAnswerEvaluation,
            MockInterviewAssessment,
            MockQuestionRubric,
        )
        Base.metadata.create_all(bind=engine)

        with engine.begin() as conn:
            try:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN resume_suggestions JSON"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE user_applications ADD COLUMN resume_suggestions JSON"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE resumes ADD COLUMN is_original_upload BOOLEAN DEFAULT 0"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE mock_answer_evaluations ADD COLUMN star_breakdown JSON NULL"))
            except Exception:
                pass
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_ai_configs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL UNIQUE,
                        active_provider VARCHAR(50) DEFAULT 'ollama',
                        selected_model VARCHAR(100),
                        gemini_model VARCHAR(100) DEFAULT 'gemini-2.5-flash',
                        openai_model VARCHAR(100) DEFAULT 'gpt-4o-mini',
                        consent_granted BOOLEAN DEFAULT 0,
                        gemini_api_key_encrypted TEXT,
                        openai_api_key_encrypted TEXT,
                        fallback_policy VARCHAR(50) DEFAULT 'deterministic',
                        created_at DATETIME,
                        updated_at DATETIME,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                """))
            except Exception:
                pass

        try:
            from .services.ai_gateway import sync_user_ai_config_on_startup
            sync_user_ai_config_on_startup()
        except Exception as seed_err:
            logger.debug(f"Initial AI config sync note: {seed_err}")

        try:
            from migrations.runner import apply_migrations
            apply_migrations(engine=engine)
        except Exception as mig_err:
            logger.warning(f"Automatic migration check encountered non-fatal note: {mig_err}")

        logger.info("Database schema verified and initialized.")
    except Exception as exc:
        logger.error(f"Error initializing database schema: {exc}")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
