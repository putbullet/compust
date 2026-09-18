"""
Unit tests verifying database resilience, SQLite auto-fallback, and clean table schema initialization.
"""

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.app.models import Base, Company, Country, Job, Resume, User
from src.app.database import init_database_schema


def test_sqlite_schema_initialization(tmp_path):
    """Verify that an empty SQLite database initializes all Compust schema tables cleanly without MySQL."""
    db_file = tmp_path / "compust_test.db"
    sqlite_url = f"sqlite:///{db_file.as_posix()}"

    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    # Core entities required by Compust
    expected_tables = [
        "countries",
        "companies",
        "company_countries",
        "scrape_targets",
        "scraping_runs",
        "jobs",
        "users",
        "user_applications",
        "user_application_history",
        "resumes",
        "customized_resumes",
    ]

    for tbl in expected_tables:
        assert tbl in table_names, f"Expected table {tbl} was not created in SQLite schema"

    # Verify session read/write on empty initialized database
    SessionTest = sessionmaker(bind=engine)
    with SessionTest() as session:
        # Initial state should be completely empty
        companies_count = session.query(Company).count()
        assert companies_count == 0

        jobs_count = session.query(Job).count()
        assert jobs_count == 0

        users_count = session.query(User).count()
        assert users_count == 0

        # Create Country and Company
        c = Country(name="Morocco", code="MA")
        session.add(c)
        session.commit()

        comp = Company(name="Acme Tech", website_url="https://acme.ma", active=True)
        session.add(comp)
        session.commit()

        assert session.query(Country).count() == 1
        assert session.query(Company).count() == 1
