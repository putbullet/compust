"""
Schema parity test: verifies that the complete migration chain
runs cleanly on both SQLite and MySQL/MariaDB and produces identical logical schemas.
"""

import pytest
from sqlalchemy import create_engine, inspect, text
from migrations.runner import apply_migrations
from src.app.database import _is_mysql_reachable


def test_schema_parity_between_sqlite_and_mysql():
    # 1. Run full schema bootstrap on fresh SQLite database
    from src.app.models import Base
    sqlite_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=sqlite_engine)
    applied_sqlite = apply_migrations(engine=sqlite_engine)
    assert len(applied_sqlite) > 0, "Expected migrations to apply on SQLite"

    sqlite_inspector = inspect(sqlite_engine)
    sqlite_tables = set(sqlite_inspector.get_table_names())
    # Exclude SQLite internal table if present
    sqlite_tables.discard("sqlite_sequence")
    sqlite_schema = {
        tbl: {col["name"] for col in sqlite_inspector.get_columns(tbl)}
        for tbl in sqlite_tables
    }

    # 2. Check if MySQL is available for dual-dialect parity check
    mysql_url = "mysql+pymysql://root:@127.0.0.1:3306/compust"
    if not _is_mysql_reachable(mysql_url):
        pytest.skip("MySQL service is not reachable on 127.0.0.1:3306; skipping live MySQL parity test")

    admin_engine = create_engine("mysql+pymysql://root:@127.0.0.1:3306/mysql")
    scratch_db = "compust_scratch_parity_test"

    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{scratch_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))

        scratch_engine = create_engine(f"mysql+pymysql://root:@127.0.0.1:3306/{scratch_db}")

        # Bootstrap MySQL scratch DB with Base.metadata then migrations
        Base.metadata.create_all(bind=scratch_engine)
        applied_mysql = apply_migrations(engine=scratch_engine)
        assert len(applied_mysql) > 0, "Expected migrations to apply on MySQL scratch database"

        mysql_inspector = inspect(scratch_engine)
        mysql_tables = set(mysql_inspector.get_table_names())
        mysql_schema = {
            tbl: {col["name"] for col in mysql_inspector.get_columns(tbl)}
            for tbl in mysql_tables
        }

        # Compare table sets (ignoring alembic_version)
        ignored_tables = {"alembic_version"}
        common_tables = (sqlite_tables & mysql_tables) - ignored_tables

        # Verify key user and AI tables are present in both
        expected_tables = {
            "users",
            "user_preferences",
            "user_ai_configs",
            "user_linkedin_profiles",
            "user_unified_profiles",
            "user_applications",
            "resumes",
            "customized_resumes",
        }
        for expected in expected_tables:
            assert expected in sqlite_tables, f"Missing {expected} in SQLite"
            assert expected in mysql_tables, f"Missing {expected} in MySQL"

        # Compare column sets for common tables
        for tbl in expected_tables:
            sqlite_cols = sqlite_schema.get(tbl, set())
            mysql_cols = mysql_schema.get(tbl, set())
            missing_in_mysql = sqlite_cols - mysql_cols
            missing_in_sqlite = mysql_cols - sqlite_cols
            assert not missing_in_mysql, f"Table {tbl} has columns in SQLite but missing in MySQL: {missing_in_mysql}"
            assert not missing_in_sqlite, f"Table {tbl} has columns in MySQL but missing in SQLite: {missing_in_sqlite}"

    finally:
        try:
            with admin_engine.connect() as conn:
                conn.execute(text(f"DROP DATABASE IF EXISTS `{scratch_db}`;"))
        except Exception:
            pass
        admin_engine.dispose()
