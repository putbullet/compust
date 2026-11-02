"""
Compust Database Schema Reconciler & Self-Healing Engine.

Provides:
1. get_schema_diff(engine): Non-destructive audit comparing SQLAlchemy Base.metadata
   against the physical database schema (tables, columns, indexes).
2. reconcile_database_schema(engine): Safe, transactional self-healing migration that
   creates missing tables, adds missing columns, verifies unique constraints,
   and applies pending SQL migrations.
3. Automated pre-migration SQLite snapshots and rollback on failure.
"""

from __future__ import annotations

import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("compust.schema_reconciler")


def _backup_sqlite_if_present(engine: Engine) -> Path | None:
    """Create a timestamped pre-repair backup of SQLite database file if it exists."""
    if engine.dialect.name != "sqlite":
        return None

    url_str = str(engine.url)
    if "sqlite:///" not in url_str:
        return None

    raw_path = url_str.split("sqlite:///", 1)[1].split("?", 1)[0]
    db_file = Path(raw_path)
    if not db_file.is_file() or db_file.stat().st_size == 0:
        return None

    try:
        from .paths import get_backups_dir
        backups_dir = get_backups_dir()
    except Exception:
        backups_dir = db_file.parent.parent / "backups"

    backups_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = backups_dir / f"compust_backup_{ts}_pre_reconciliation.db"
    try:
        shutil.copy2(db_file, backup_path)
        logger.info(f"Automated SQLite backup created prior to schema reconciliation: {backup_path}")
        return backup_path
    except Exception as exc:
        logger.warning(f"Could not create SQLite backup before reconciliation: {exc}")
        return None


def get_schema_diff(engine: Engine) -> dict[str, Any]:
    """
    Compare SQLAlchemy Declarative Base metadata against the connected database schema.
    Returns details on missing tables and missing columns per table.
    """
    from .models import Base
    from .models_mock_interview import (
        MockInterviewSession,
        MockInterviewTurn,
        MockAnswerEvaluation,
        MockInterviewAssessment,
        MockQuestionRubric,
    )

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            missing_tables.append(table_name)
            missing_columns[table_name] = [c.name for c in table.columns]
        else:
            actual_cols = {col["name"].lower() for col in inspector.get_columns(table_name)}
            missing_in_table = [
                c.name for c in table.columns if c.name.lower() not in actual_cols
            ]
            if missing_in_table:
                missing_columns[table_name] = missing_in_table

    is_synced = len(missing_tables) == 0 and len(missing_columns) == 0
    return {
        "is_synced": is_synced,
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "total_expected_tables": len(Base.metadata.tables),
        "existing_tables_count": len(existing_tables),
    }


def _column_type_to_sql(col, dialect) -> str:
    """Compile column type for dialect, stripping incompatible clauses."""
    compiled_type = col.type.compile(dialect=dialect)
    # SQLite compatibility for UNSIGNED INT / TINYINT
    if dialect.name == "sqlite":
        compiled_type = re.sub(r"\bINT\s+UNSIGNED\b", "INTEGER", compiled_type, flags=re.IGNORECASE)
        compiled_type = re.sub(r"\bTINYINT\(1\)\b", "BOOLEAN", compiled_type, flags=re.IGNORECASE)
        compiled_type = re.sub(r"\bMEDIUMTEXT\b", "TEXT", compiled_type, flags=re.IGNORECASE)
        compiled_type = re.sub(r"\bDATETIME\b", "DATETIME", compiled_type, flags=re.IGNORECASE)

    sql_parts = [col.name, compiled_type]

    # Handle defaults
    if col.default is not None and hasattr(col.default, "arg"):
        arg = col.default.arg
        if isinstance(arg, bool):
            sql_parts.append(f"DEFAULT {1 if arg else 0}")
        elif isinstance(arg, (int, float)):
            sql_parts.append(f"DEFAULT {arg}")
        elif isinstance(arg, str):
            sql_parts.append(f"DEFAULT '{arg}'")
    elif col.server_default is not None and hasattr(col.server_default, "arg"):
        sql_parts.append(f"DEFAULT {col.server_default.arg}")

    # Nullability: in SQLite ALTER TABLE ADD COLUMN, cannot add NOT NULL without a default
    if not col.nullable:
        if dialect.name == "sqlite":
            # Only add NOT NULL if there is a default
            if "DEFAULT" in " ".join(sql_parts):
                sql_parts.append("NOT NULL")
        else:
            sql_parts.append("NOT NULL")

    return " ".join(sql_parts)


def reconcile_database_schema(engine: Engine, auto_backup: bool = True) -> dict[str, Any]:
    """
    Self-healing database schema synchronizer.
    1. Backs up SQLite database if present.
    2. Creates missing tables from Base.metadata.
    3. Adds any missing columns to existing tables dynamically.
    4. Ensures critical unique indexes exist (e.g. users.email).
    5. Runs incremental SQL migrations.
    6. Confirms schema health.
    Rolls back to pre-repair backup if an unhandled failure occurs on SQLite.
    """
    from .models import Base
    from .models_mock_interview import (
        MockInterviewSession,
        MockInterviewTurn,
        MockAnswerEvaluation,
        MockInterviewAssessment,
        MockQuestionRubric,
    )

    backup_file: Path | None = None
    if auto_backup:
        backup_file = _backup_sqlite_if_present(engine)

    dialect = engine.dialect
    is_sqlite = dialect.name == "sqlite"
    added_columns_log: dict[str, list[str]] = {}
    created_tables_log: list[str] = []

    try:
        # Step 1: Ensure all base tables exist
        inspector = inspect(engine)
        existing_tables_before = set(inspector.get_table_names())
        Base.metadata.create_all(bind=engine)

        inspector = inspect(engine)
        existing_tables_after = set(inspector.get_table_names())
        created_tables_log = list(existing_tables_after - existing_tables_before)
        if created_tables_log:
            logger.info(f"Created {len(created_tables_log)} missing table(s): {', '.join(created_tables_log)}")

        # Step 2: Inspect existing tables and add any missing columns
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables_after:
                continue

            actual_cols = {col["name"].lower() for col in inspector.get_columns(table_name)}
            missing_cols = [c for c in table.columns if c.name.lower() not in actual_cols]

            if missing_cols:
                added_columns_log[table_name] = []
                with engine.begin() as conn:
                    for col in missing_cols:
                        col_def = _column_type_to_sql(col, dialect)
                        alter_stmt = f"ALTER TABLE {table_name} ADD COLUMN {col_def}"
                        try:
                            conn.execute(text(alter_stmt))
                            added_columns_log[table_name].append(col.name)
                            logger.info(f"Auto-healed missing column: {table_name}.{col.name}")
                        except Exception as col_err:
                            err_msg = str(col_err).lower()
                            if "duplicate column" in err_msg or "already exists" in err_msg:
                                pass
                            else:
                                logger.error(f"Failed to add column {table_name}.{col.name}: {col_err}")
                                raise

        # Step 3: Ensure critical indexes exist (e.g. users.email unique index)
        with engine.begin() as conn:
            try:
                if is_sqlite:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email ON users (email)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_active ON jobs (active)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_company_id ON jobs (company_id)"))
                else:
                    # MySQL index creation if not exists
                    try:
                        conn.execute(text("CREATE UNIQUE INDEX uq_users_email ON users (email)"))
                    except Exception:
                        pass
                    try:
                        conn.execute(text("CREATE INDEX ix_jobs_active ON jobs (active)"))
                    except Exception:
                        pass
            except Exception as idx_err:
                logger.debug(f"Index creation note: {idx_err}")

        # Step 4: Run SQL migrations to ensure seed data & custom triggers/indexes are applied
        applied_migrations: list[str] = []
        try:
            from migrations.runner import apply_migrations
            applied_migrations = apply_migrations(engine=engine)
            if applied_migrations:
                logger.info(f"Applied {len(applied_migrations)} SQL migration(s): {', '.join(applied_migrations)}")
        except Exception as mig_err:
            logger.warning(f"SQL migrations runner completed with note: {mig_err}")

        # Step 5: Final verification check
        final_diff = get_schema_diff(engine)
        if not final_diff["is_synced"]:
            logger.warning(f"Schema reconciliation completed with outstanding differences: {final_diff}")

        return {
            "success": True,
            "created_tables": created_tables_log,
            "added_columns": added_columns_log,
            "applied_migrations": applied_migrations,
            "is_synced": final_diff["is_synced"],
            "backup_file": str(backup_file) if backup_file else None,
        }

    except Exception as exc:
        logger.error(f"Fatal error during schema reconciliation: {exc}", exc_info=True)
        # Rollback SQLite if backup exists
        if backup_file and backup_file.is_file() and is_sqlite:
            try:
                raw_path = str(engine.url).split("sqlite:///", 1)[1].split("?", 1)[0]
                target_file = Path(raw_path)
                shutil.copy2(backup_file, target_file)
                logger.info(f"Rolled back SQLite database to pre-repair state: {backup_file}")
            except Exception as rb_err:
                logger.error(f"Failed to restore SQLite backup: {rb_err}")
        raise RuntimeError(f"Database schema reconciliation failed: {exc}") from exc
