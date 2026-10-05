"""
Compust User Data and Storage Paths Management.

Ensures all dynamic, persistent user data (database, uploaded resumes,
generated documents, logs, downloaded model files, and database backups)
lives outside the installation directory in a per-user directory:
- Windows: %LOCALAPPDATA%\\Compust (e.g. C:\\Users\\<Username>\\AppData\\Local\\Compust)
- Linux / macOS: ~/.compust
- Override: via COMPUST_USER_DATA_DIR environment variable
"""

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


def get_app_mode() -> str:
    """
    Return the current runtime mode: 'installed' or 'dev'.
    Prioritizes COMPUST_APP_MODE env var, then detects marker vs git repo.
    """
    env_mode = os.environ.get("COMPUST_APP_MODE")
    if env_mode:
        return env_mode.lower()
    
    # If .install_complete exists and no .git directory exists -> installed
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    if (repo_root / ".install_complete").is_file() and not (repo_root / ".git").exists():
        return "installed"
    return "dev"


def get_user_data_dir() -> Path:
    """
    Return the absolute path to the data directory.
    - Installed mode: %LOCALAPPDATA%\\Compust (or ~/.compust on Unix)
    - Dev mode: <repo_root>/important/data (or <repo_root>/data)
    - Override: COMPUST_USER_DATA_DIR environment variable
    """
    # 1. Direct environment variable override
    env_dir = os.environ.get("COMPUST_USER_DATA_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    mode = get_app_mode()
    if mode == "dev":
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        p = repo_root / "important" / "data"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 2. Windows standard per-user local app data (%LOCALAPPDATA%\Compust)
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            p = Path(local_app_data) / "Compust"
        else:
            p = Path.home() / "AppData" / "Local" / "Compust"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 3. Unix standard (~/.compust)
    p = Path.home() / ".compust"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_database_dir() -> Path:
    """Directory holding SQLite database files."""
    d = get_user_data_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_database_path() -> Path:
    """
    Return path to the primary SQLite database file.
    Preserves and seamlessly aliases older compust_local.db if present.
    """
    db_dir = get_database_dir()
    primary_db = db_dir / "compust.db"
    legacy_db = db_dir / "compust_local.db"

    if not primary_db.exists() and legacy_db.exists():
        return legacy_db

    return primary_db


def get_storage_dir(subdir: str = "") -> Path:
    """Directory holding uploaded resumes, customized versions, and exported docs."""
    base = get_user_data_dir() / "storage"
    if subdir:
        base = base / subdir
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_logs_dir() -> Path:
    """Directory holding application logs (launcher.log, backend.log, frontend.log)."""
    d = get_user_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_models_dir() -> Path:
    """Directory holding cached local AI / Whisper STT models."""
    d = get_user_data_dir() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_backups_dir() -> Path:
    """Directory holding timestamped pre-migration SQLite backups."""
    d = get_user_data_dir() / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def backup_sqlite_database(db_file: Path, max_backups: int = 5) -> Path | None:
    """
    Create a timestamped backup of the given SQLite database before applying migrations.
    Prunes older backups to keep at most `max_backups` files.
    """
    if not db_file.exists() or db_file.stat().st_size == 0:
        return None

    backups_dir = get_backups_dir()
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = backups_dir / f"{db_file.stem}_backup_{now_str}.db"

    try:
        shutil.copy2(db_file, backup_file)
    except Exception:
        return None

    # Prune old backups keeping only the most recent `max_backups`
    try:
        existing = sorted(
            backups_dir.glob(f"{db_file.stem}_backup_*.db"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for old in existing[max_backups:]:
            try:
                old.unlink()
            except Exception:
                pass
    except Exception:
        pass

    return backup_file
