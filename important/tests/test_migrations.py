from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from migrations.runner import apply_migrations, _ensure_migrations_table


def test_migrations_apply_in_order_and_record_versions(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    # Monkeypatch get_settings to return this sqlite url
    class MockSettings:
        database_url = "sqlite://"

    monkeypatch.setattr("migrations.runner.get_settings", lambda: MockSettings())
    monkeypatch.setattr("migrations.runner.create_engine", lambda *a, **kw: engine)
    monkeypatch.setattr(engine, "dispose", lambda: None)

    applied = apply_migrations()
    assert "001_create_scrape_targets.sql" in applied
    assert "002_create_scraping_runs.sql" in applied
    assert "003_add_scrape_target_cooldown.sql" in applied
    assert "004_add_salary_compliance_user_fields.sql" in applied
    assert "005_add_scrape_target_provenance_and_indexes.sql" in applied
    assert "006_create_user_profile_tables.sql" in applied
    assert "007_create_user_applications.sql" in applied
    assert "008_create_job_translations.sql" in applied

    # Verify tables exist
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert "schema_migrations" in table_names
    assert "scrape_targets" in table_names
    assert "scraping_runs" in table_names
    assert "user_applications" in table_names
    assert "job_translations" in table_names

    # Calling apply_migrations again should apply 0 new migrations
    second_run = apply_migrations()
    assert second_run == []
