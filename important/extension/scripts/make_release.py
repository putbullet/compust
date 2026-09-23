#!/usr/bin/env python3
"""
make_release.py — Build the AMO submission archives for Compust Capture.

Produces:
  release/firefox-amo/compust-capture-firefox-v<version>.zip
      The built Firefox extension (copied from dist/compust-capture-firefox.zip).
  release/firefox-amo/compust-capture-firefox-v<version>-source.zip
      The TypeScript source tree + BUILD.md, packaged with POSIX-compliant
      entry names (forward slashes only, as required by the ZIP spec and AMO).

Usage:
  python scripts/make_release.py
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT     = Path(__file__).resolve().parent.parent.parent  # a:\code\compust\important
EXTENSION_DIR = Path(__file__).resolve().parent.parent          # a:\code\compust\important\extension
RELEASE_DIR   = REPO_ROOT / "release" / "firefox-amo"

# Read version from extension/package.json
import json
with open(EXTENSION_DIR / "package.json", encoding="utf-8") as f:
    VERSION = json.load(f)["version"]

PROD_ZIP_NAME   = f"compust-capture-firefox-v{VERSION}.zip"
SOURCE_ZIP_NAME = f"compust-capture-firefox-v{VERSION}-source.zip"
BUILD_MD        = RELEASE_DIR / "BUILD.md"

# Directories / patterns to exclude from source archive
EXCLUDE_DIRS = {"node_modules", "dist", ".git", "__pycache__"}
EXCLUDE_SUFFIXES = {".pyc"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def posix_arcname(abs_path: Path, root: Path) -> str:
    """Return the archive entry name for abs_path, always using '/' separators."""
    return abs_path.relative_to(root).as_posix()


def collect_source_files(base: Path) -> list[tuple[Path, str]]:
    """
    Walk base recursively, skipping excluded dirs/files.
    Returns list of (absolute_path, posix_arcname) pairs.
    """
    results = []
    for dirpath, dirnames, filenames in os.walk(base):
        # Prune excluded directories in-place so os.walk won't recurse into them
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for filename in filenames:
            abs_path = Path(dirpath) / filename
            if abs_path.suffix in EXCLUDE_SUFFIXES:
                continue
            # arcname is relative to REPO_ROOT so entries look like:
            #   extension/src/content/common/overlay.ts
            arcname = posix_arcname(abs_path, REPO_ROOT)
            results.append((abs_path, arcname))
    return results


def verify_no_backslashes(zip_path: Path) -> int:
    """Open zip_path and assert every entry uses only forward slashes. Returns entry count."""
    bad = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if "\\" in name:
                bad.append(name)
    if bad:
        print(f"  ERROR: {len(bad)} entries with backslashes in {zip_path.name}:")
        for b in bad[:8]:
            print(f"    {b}")
        sys.exit(1)
    return len(zf.namelist()) if False else sum(1 for _ in zipfile.ZipFile(zip_path).namelist())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Production Firefox zip (built by adm-zip in build.js — already correct)
    src_prod = EXTENSION_DIR / "dist" / "compust-capture-firefox.zip"
    dst_prod = RELEASE_DIR / PROD_ZIP_NAME
    if not src_prod.exists():
        print(f"ERROR: Built production zip not found at {src_prod}")
        print("       Run 'node build.js firefox' first.")
        sys.exit(1)
    shutil.copy2(src_prod, dst_prod)
    count_prod = verify_no_backslashes(dst_prod)
    print(f"[OK] Production zip  : {dst_prod.name}  ({dst_prod.stat().st_size // 1024} KB, {count_prod} entries, all forward-slash)")

    # 2. Source code archive — built here with explicit POSIX arcnames
    dst_src = RELEASE_DIR / SOURCE_ZIP_NAME
    if dst_src.exists():
        dst_src.unlink()

    files = collect_source_files(EXTENSION_DIR)

    # Also include BUILD.md at archive root if it exists
    build_md_entry = None
    if BUILD_MD.exists():
        build_md_entry = (BUILD_MD, "BUILD.md")

    total = len(files) + (1 if build_md_entry else 0)
    print(f"     Collecting {len(files)} source files + BUILD.md -> {SOURCE_ZIP_NAME}")

    with zipfile.ZipFile(dst_src, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if build_md_entry:
            abs_path, arcname = build_md_entry
            zf.write(abs_path, arcname)
        for abs_path, arcname in sorted(files, key=lambda x: x[1]):
            zf.write(abs_path, arcname)

    count_src = verify_no_backslashes(dst_src)
    print(f"[OK] Source archive  : {dst_src.name}  ({dst_src.stat().st_size // 1024} KB, {count_src} entries, all forward-slash)")

    print()
    print("All archives ready:")
    for f in sorted(RELEASE_DIR.iterdir()):
        if f.is_file():
            print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")
    print(f"\nLocation: {RELEASE_DIR}")


if __name__ == "__main__":
    main()
