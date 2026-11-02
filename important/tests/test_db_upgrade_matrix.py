"""Automated test suite for Database Upgrades, Schema Reconciler, Multi-Port Probing, and Import Ledger."""

import os
import tempfile
import sqlite3
import pytest
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from src.app.models import Base, User, Job, Company, Country, ImportBatch
from src.app.schema_reconciler import reconcile_database_schema, get_schema_diff
from src.app.schemas_data import (
    ImportSourceInfo,
    UserDataSummary,
    ImportSourcesResponse,
    ImportPreviewRequest,
    ImportExecuteRequest,
)
from src.app.services.db_config import (
    encrypt_password,
    decrypt_password,
    save_db_config,
    load_db_config,
    clear_db_config,
    probe_mysql_handshake,
)
from src.app.services.data_manager import DataManagerService


def test_schema_reconciler_auto_heals_truncated_tables(tmp_path):
    """Simulate the installer failure: stub tables with missing columns are repaired safely."""
    test_db = tmp_path / "test_corrupt.db"
    conn = sqlite3.connect(test_db)
    cur = conn.cursor()

    # Create the exact corrupt tables that migration 004 fallback generated:
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email_verified BOOLEAN, is_active BOOLEAN);")
    cur.execute("INSERT INTO users (id, email_verified, is_active) VALUES (1, 1, 1);")

    cur.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, salary_min INTEGER, salary_max INTEGER);")
    cur.execute("INSERT INTO jobs (id, salary_min, salary_max) VALUES (1, 50000, 80000);")
    conn.commit()
    conn.close()

    engine = create_engine(f"sqlite:///{test_db}")

    # Verify corrupt initial state
    diff_before = get_schema_diff(engine)
    assert not diff_before["is_synced"]
    assert "users" in diff_before["missing_columns"]
    assert "email" in diff_before["missing_columns"]["users"]
    assert "jobs" in diff_before["missing_columns"]
    assert "title" in diff_before["missing_columns"]["jobs"]

    # Execute auto-repair reconciler
    res = reconcile_database_schema(engine, auto_backup=True)
    assert res["is_synced"] is True
    assert "users" in res["added_columns"]
    assert "email" in res["added_columns"]["users"]

    # Verify that existing row was NOT lost
    with engine.connect() as check_conn:
        user_row = check_conn.execute(text("SELECT id, email_verified, is_active, email FROM users WHERE id = 1")).fetchone()
        assert user_row[0] == 1
        assert user_row[1] == 1

        job_row = check_conn.execute(text("SELECT id, salary_min, salary_max, title, active FROM jobs WHERE id = 1")).fetchone()
        assert job_row[0] == 1
        assert job_row[1] == 50000

    # Verify final schema diff is completely synced
    diff_after = get_schema_diff(engine)
    assert diff_after["is_synced"] is True
    assert len(diff_after["missing_tables"]) == 0
    assert len(diff_after["missing_columns"]) == 0


def test_dpapi_password_encryption_roundtrip(tmp_path, monkeypatch):
    """Test that passwords encrypted via DPAPI round-trip correctly and config persists."""
    secret = "TopSecretPassword123!@#"
    enc = encrypt_password(secret)
    dec = decrypt_password(enc)
    assert dec == secret

    # Save to a temporary config path
    cfg_file = tmp_path / "db_config.json"
    monkeypatch.setattr("src.app.services.db_config.get_db_config_file", lambda: cfg_file)

    save_db_config(
        engine_type="mysql",
        host="127.0.0.1",
        port=3306,
        user="root",
        password=secret,
        database="compust_test",
    )
    assert cfg_file.is_file()

    loaded = load_db_config()
    assert loaded is not None
    assert loaded["engine"] == "mysql"
    assert loaded["user"] == "root"
    assert loaded["database"] == "compust_test"
    assert decrypt_password(loaded["password_encrypted"]) == secret

    clear_db_config()
    assert not cfg_file.is_file()


def test_import_dry_run_and_undo_flow(tmp_path, monkeypatch):
    """Test that dry-run commits zero rows, execution records ledger, and undo cleanly rolls back."""
    # Source DB
    src_db = tmp_path / "source.db"
    src_engine = create_engine(f"sqlite:///{src_db}")
    Base.metadata.create_all(bind=src_engine)

    with Session(src_engine) as session:
        now = datetime.now(timezone.utc)
        cntry = Country(id=1, name="United States", code="US")
        u = User(id=1, email="alice@example.com", password_hash="hash", is_active=True, created_at=now, updated_at=now)
        c = Company(id=1, name="Acme Corp", website_url="https://acme.com", careers_url="https://acme.com/careers", active=True)
        j = Job(id=1, company_id=1, country_id=1, title="Senior Engineer", job_url="https://acme.com/jobs/1", active=True, description="Do cool things", discovered_at=now, created_at=now, updated_at=now)
        session.add_all([cntry, u, c, j])
        session.commit()

    # Target DB
    dst_db = tmp_path / "target.db"
    dst_engine = create_engine(f"sqlite:///{dst_db}")
    Base.metadata.create_all(bind=dst_engine)

    # Monkeypatch data_manager to use dst_engine as its active database
    from sqlalchemy.orm import sessionmaker
    import src.app.services.data_manager as dm_mod
    monkeypatch.setattr(dm_mod, "engine", dst_engine)
    monkeypatch.setattr(dm_mod, "SessionLocal", sessionmaker(bind=dst_engine))
    monkeypatch.setattr("src.app.paths.get_database_path", lambda: dst_db)

    # Instantiate data manager service
    dm = DataManagerService()

    # Mock discover_sources to return src_db as a discovered source
    mock_source = ImportSourceInfo(
        id="test_sqlite_src",
        name="Mock Source SQLite",
        type="sqlite",
        location=str(src_db),
        total_jobs=1,
        total_companies=1,
        reachable=True,
        status_message="Ready",
        users=[
            UserDataSummary(
                id=1,
                email="alice@example.com",
                first_name="Alice",
                last_name="Tester",
                applications_count=0,
                contacts_count=0,
                resumes_count=0,
            )
        ],
    )
    mock_sources_resp = ImportSourcesResponse(
        sources=[mock_source],
        target_database_path=str(dst_db),
        target_database_type="sqlite",
        target_has_data=False,
        target_stats={},
    )
    monkeypatch.setattr(dm, "discover_sources", lambda: mock_sources_resp)

    # 1. Preview
    preview_req = ImportPreviewRequest(source_id="test_sqlite_src", user_id=1)
    preview = dm.preview_import(preview_req)
    assert preview.jobs_count == 1
    assert preview.companies_count == 1

    # 2. Dry run simulation
    dry_req = ImportExecuteRequest(source_id="test_sqlite_src", user_id=1, dry_run=True)
    dry_res = dm.execute_import(dry_req)
    assert dry_res.success is True
    assert dry_res.jobs_imported == 1

    # Assert target database still has ZERO rows
    with dst_engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM companies")).scalar() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM import_batches")).scalar() == 0

    # 3. Real Import Execution
    real_req = ImportExecuteRequest(source_id="test_sqlite_src", user_id=1, dry_run=False)
    real_res = dm.execute_import(real_req)
    assert real_res.success is True
    assert real_res.jobs_imported == 1

    # Assert target database now has rows and ledger entry
    with dst_engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM companies")).scalar() == 1
        batches = conn.execute(text("SELECT batch_id, status FROM import_batches")).fetchall()
        assert len(batches) == 1
        batch_id = batches[0][0]
        assert batches[0][1] == "completed"

    # 4. Undo Import
    undo_res = dm.undo_import(batch_id=batch_id)
    assert undo_res.success is True

    # Assert target database rows were safely removed and ledger marked undone
    with dst_engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar() == 0
        assert conn.execute(text("SELECT COUNT(*) FROM companies")).scalar() == 0
        status = conn.execute(text("SELECT status FROM import_batches WHERE batch_id = :b"), {"b": batch_id}).scalar()
        assert status == "undone"


def test_migration_files_sequential_and_valid():
    """Verify all 20 SQL migration files exist sequentially and are non-empty."""
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))
    assert len(sql_files) >= 20

    for i in range(1, 21):
        expected_prefix = f"{i:03d}_"
        matching = [f for f in sql_files if f.name.startswith(expected_prefix)]
        assert len(matching) == 1, f"Missing migration with prefix {expected_prefix}"
        assert matching[0].stat().st_size > 0, f"Migration {matching[0].name} is empty"
