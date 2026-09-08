from sqlalchemy import create_engine, text

from src.app.config import get_settings


def seed_from_company_careers_urls() -> int:
    """Insert one careers target per existing company URL, without duplicates."""
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        statement = text(
            """
            INSERT INTO scrape_targets (company_id, url, type, active)
            SELECT c.id, c.careers_url, 'careers', c.active
            FROM companies AS c
            WHERE c.careers_url IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM scrape_targets AS st
                  WHERE st.company_id = c.id
                    AND st.url = c.careers_url
              )
            """
        )
        with engine.begin() as connection:
            result = connection.execute(statement)
            return result.rowcount
    finally:
        engine.dispose()


if __name__ == "__main__":
    print(f"Inserted {seed_from_company_careers_urls()} scrape target(s).")
