from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from src.app.config import get_settings

MIGRATIONS_DIR = Path(__file__).parent


def _ensure_migrations_table(connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(100) NOT NULL PRIMARY KEY,
                applied_at DATETIME NOT NULL
            )
            """
        )
    )


def _clean_for_sqlite(sql: str) -> str:
    import re
    # Remove MySQL-specific engine/charset clauses while preserving the terminating semicolon
    sql = re.sub(r"\)\s*ENGINE=[^;\n]*;?", ");", sql, flags=re.IGNORECASE)
    # Convert INT UNSIGNED AUTO_INCREMENT to INTEGER PRIMARY KEY if needed, or remove AUTO_INCREMENT
    sql = re.sub(r"\bAUTO_INCREMENT\b", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bINT\s+UNSIGNED\b", "INTEGER", sql, flags=re.IGNORECASE)
    # Remove index prefix lengths like job_url(255)
    sql = re.sub(r"\((\d+)\)", "", sql)
    # Remove inline MySQL INDEX lines inside CREATE TABLE or ADD CONSTRAINT or CREATE INDEX for SQLite compatibility
    lines = []
    for line in sql.splitlines():
        trimmed = line.strip()
        if trimmed.upper().startswith("INDEX "):
            continue
        if "ADD CONSTRAINT" in trimmed.upper():
            continue
        if trimmed.upper().startswith("CREATE INDEX"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r",\s*\)", "\n)", cleaned)
    return cleaned


def apply_migrations() -> list[str]:
    """Run pending SQL migrations in order and track them in schema_migrations."""
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    applied: list[str] = []

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        with engine.begin() as connection:
            _ensure_migrations_table(connection)

            already_applied = set(
                row[0]
                for row in connection.execute(
                    text("SELECT version FROM schema_migrations")
                ).fetchall()
            )

            # If scrape_targets was created prior to schema_migrations, record 001 as applied
            if (
                "001_create_scrape_targets.sql" not in already_applied
                and "scrape_targets" in existing_tables
            ):
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                connection.execute(
                    text(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (:version, :applied_at)"
                    ),
                    {"version": "001_create_scrape_targets.sql", "applied_at": now},
                )
                already_applied.add("001_create_scrape_targets.sql")

            is_sqlite = engine.dialect.name == "sqlite"
            sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
            for sql_file in sql_files:
                version = sql_file.name
                if version in already_applied:
                    continue

                sql_content = sql_file.read_text(encoding="utf-8").strip()
                if is_sqlite:
                    sql_content = _clean_for_sqlite(sql_content)
                if sql_content:
                    # Execute statements
                    for statement in sql_content.split(";"):
                        stmt = statement.strip()
                        if stmt:
                            if is_sqlite:
                                import re
                                match = re.match(r"^ALTER\s+TABLE\s+(\w+)", stmt, re.IGNORECASE)
                                if match:
                                    table_name = match.group(1)
                                    check = connection.execute(
                                        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:tbl"),
                                        {"tbl": table_name},
                                    ).fetchone()
                                    if not check:
                                        connection.execute(text(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY)"))
                            connection.execute(text(stmt))

                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                connection.execute(
                    text(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (:version, :applied_at)"
                    ),
                    {"version": version, "applied_at": now},
                )
                applied.append(version)

        return applied
    finally:
        engine.dispose()


def apply_migration() -> bool:
    """Backward-compatible wrapper for single-migration callers."""
    applied = apply_migrations()
    return len(applied) > 0


if __name__ == "__main__":
    newly_applied = apply_migrations()
    if newly_applied:
        print(f"Applied {len(newly_applied)} migration(s): {', '.join(newly_applied)}")
    else:
        print("No pending migrations; database schema is up to date.")
