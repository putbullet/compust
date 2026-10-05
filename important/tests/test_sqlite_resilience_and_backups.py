"""
Automated validation of SQLite Resilient Engine, Per-User Paths, and Pre-Migration Backups.
"""

from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from src.app.paths import get_user_data_dir, get_database_path, get_backups_dir, backup_sqlite_database
from migrations.runner import apply_migrations


def test_per_user_paths_resolution(monkeypatch, tmp_path):
    """Verify that user data directories resolve inside COMPUST_USER_DATA_DIR."""
    custom_dir = tmp_path / "compust_test_userdata"
    monkeypatch.setenv("COMPUST_USER_DATA_DIR", str(custom_dir))

    user_dir = get_user_data_dir()
    assert user_dir == custom_dir
    assert user_dir.is_dir()

    db_path = get_database_path()
    assert str(custom_dir) in str(db_path)
    assert db_path.name == "compust.db"

    backups_dir = get_backups_dir()
    assert str(custom_dir) in str(backups_dir)
    assert backups_dir.is_dir()


def test_sqlite_backup_creation_and_pruning(monkeypatch, tmp_path):
    """Verify that backup_sqlite_database makes timestamped copies and prunes excess."""
    monkeypatch.setenv("COMPUST_USER_DATA_DIR", str(tmp_path))

    db_file = tmp_path / "test.db"
    db_file.write_bytes(b"SQLite format 3\x00Dummy DB data for test")

    # Make 6 backups
    for i in range(6):
        # ensure distinct names or simulated entries
        b = backup_sqlite_database(db_file, max_backups=3)
        assert b is not None and b.exists()

    backups = list(get_backups_dir().glob("test_backup_*.db"))
    # Should be pruned to at most 3
    assert len(backups) <= 3


def test_fresh_sqlite_database_migrations(monkeypatch, tmp_path):
    """Verify apply_migrations runs cleanly from scratch on a brand new SQLite database."""
    fresh_db = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{fresh_db.as_posix()}", connect_args={"check_same_thread": False})

    try:
        applied = apply_migrations(engine=engine)
        assert len(applied) > 0

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert "schema_migrations" in tables
        assert "user_applications" in tables
        assert "scrape_targets" in tables

        # Second run should be a no-op
        second = apply_migrations(engine=engine)
        assert len(second) == 0
    finally:
        engine.dispose()
