from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from src.app.config import get_settings

MIGRATION_FILE = Path(__file__).with_name("001_create_scrape_targets.sql")


def apply_migration() -> bool:
    """Create scrape_targets if it is absent; return whether DDL was executed."""
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        if "scrape_targets" in inspector.get_table_names():
            return False
        with engine.begin() as connection:
            connection.execute(text(MIGRATION_FILE.read_text(encoding="utf-8")))
        return True
    finally:
        engine.dispose()


if __name__ == "__main__":
    created = apply_migration()
    print("Created scrape_targets." if created else "scrape_targets already exists; no changes made.")
