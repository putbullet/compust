"""
Compust Windows Release Packaging Script.
Builds the production React frontend, packages the FastAPI application with
empty initialized SQLite database support, and creates a portable Windows release zip
with SHA-256 checksums ready for GitHub Releases.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VERSION = "1.0.0"
RELEASE_NAME = f"Compust-Windows-Portable-v{VERSION}"


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192 * 16):
            sha.update(chunk)
    return sha.hexdigest()


def build_release():
    print("=" * 65)
    print(f"Starting Compust Windows Release Build [{VERSION}]")
    print("=" * 65)

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    important_dir = repo_root / "important"
    frontend_dir = important_dir / "frontend"
    release_root = repo_root / "release"
    target_dir = release_root / RELEASE_NAME

    # 1. Build React Frontend SPA
    print("\n[1/5] Building production React frontend (dist)...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    try:
        subprocess.run(
            [npm_cmd, "run", "build"],
            cwd=str(frontend_dir),
            check=True,
            shell=True if os.name == "nt" else False,
        )
        dist_index = frontend_dir / "dist" / "index.html"
        assert dist_index.is_file(), "frontend/dist/index.html was not generated!"
        print("[OK] Frontend built successfully.")
    except Exception as exc:
        print(f"ERROR: Frontend build failed: {exc}")
        sys.exit(1)

    # 2. Clean and create release directory
    print(f"\n[2/5] Preparing clean release directory: {target_dir}...")
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # 3. Copy launcher files
    print("\n[3/5] Copying launcher & startup scripts...")
    shutil.copy2(repo_root / "Compust.bat", target_dir / "Compust.bat")
    
    # Launcher folder
    launcher_dst = target_dir / "launcher"
    launcher_dst.mkdir(exist_ok=True)
    for l_file in ["launcher_core.py", "create_shortcut.py", "generate_icon.py", "compust.ico"]:
        src_f = repo_root / "launcher" / l_file
        if src_f.exists():
            shutil.copy2(src_f, launcher_dst / l_file)

    # 4. Copy backend application (clean, no dev caches or dev db)
    print("\n[4/5] Bundling application source and assets...")
    imp_dst = target_dir / "important"
    imp_dst.mkdir(exist_ok=True)

    # Copy src
    shutil.copytree(
        important_dir / "src",
        imp_dst / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )

    # Copy frontend dist (compiled SPA)
    shutil.copytree(
        frontend_dir / "dist",
        imp_dst / "frontend" / "dist",
    )

    # Copy frontend public illustrations (for educational diagrams)
    pub_illustrations = frontend_dir / "public" / "illustrations"
    if pub_illustrations.is_dir():
        shutil.copytree(
            pub_illustrations,
            imp_dst / "frontend" / "public" / "illustrations",
            ignore=shutil.ignore_patterns("__pycache__"),
        )

    # Copy alembic migrations
    if (important_dir / "alembic").is_dir():
        shutil.copytree(
            important_dir / "alembic",
            imp_dst / "alembic",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        if (important_dir / "alembic.ini").is_file():
            shutil.copy2(important_dir / "alembic.ini", imp_dst / "alembic.ini")

    # Create empty data directory for standalone SQLite database
    (imp_dst / "data").mkdir(exist_ok=True)
    (target_dir / "logs").mkdir(exist_ok=True)

    # Copy README & docs
    shutil.copy2(repo_root / "README.md", target_dir / "README.md")
    if (repo_root / "COMPUS_DEVELOPER_GUIDE.md").is_file():
        shutil.copy2(repo_root / "COMPUS_DEVELOPER_GUIDE.md", target_dir / "COMPUS_DEVELOPER_GUIDE.md")

    # Write simple quickstart readme
    quickstart_content = f"""# Compust — Windows Portable Release (v{VERSION})

Welcome to Compust, the open-source, local-first career intelligence, resume tailoring, and technical interview preparation platform.

## Quick Start (No Setup Required)

1. Double-click `Compust.bat` (or create a desktop shortcut by running `launcher\\create_shortcut.py`).
2. Compust starts automatically:
   - Evaluates local database connectivity (auto-initializes local database with empty schema).
   - Starts the local career intelligence backend.
   - Automatically opens your default web browser to the platform.
3. You can immediately begin adding verified employer career portals, editing resumes, and practicing interview questions!

## Data & Storage
- Your data is stored locally on your machine in `important/data/`.
- Zero tracking, zero telemetry, 100% private and offline-capable.
"""
    (target_dir / "QUICKSTART.txt").write_text(quickstart_content, encoding="utf-8")

    # 5. Create Zip Archive & Checksums
    print(f"\n[5/5] Creating portable distribution archive ({RELEASE_NAME}.zip)...")
    zip_path = release_root / f"{RELEASE_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                abs_p = Path(root) / file
                rel_p = abs_p.relative_to(release_root)
                zf.write(abs_p, rel_p)

    checksum = compute_sha256(zip_path)
    checksum_file = release_root / f"{RELEASE_NAME}.zip.sha256"
    checksum_file.write_text(f"{checksum}  {RELEASE_NAME}.zip\n", encoding="utf-8")

    print("\n" + "=" * 65)
    print("✓ Compust Windows Release Build Completed Successfully!")
    print(f"  Archive:  {zip_path} ({round(zip_path.stat().st_size / (1024 * 1024), 2)} MB)")
    print(f"  SHA-256:  {checksum}")
    print("=" * 65)


if __name__ == "__main__":
    build_release()
