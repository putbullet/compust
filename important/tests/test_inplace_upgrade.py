"""
Test in-place upgrade of Compust-Setup-v1.0.2.exe against installed instance.
Verifies that %LOCALAPPDATA%\\Compust\\data\\compust.db and user settings survive intact.
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

def test_inplace_upgrade():
    local_app = Path(os.environ.get("LOCALAPPDATA", "")) / "Compust"
    db_path = local_app / "data" / "compust.db"
    ai_config_path = local_app / "ai_config.json"
    installer_exe = Path("A:/code/compust/release/Compust-Setup-v1.0.2.exe")
    install_target = Path("A:/Compust")

    print("=" * 60)
    print("STARTING IN-PLACE UPGRADE TEST: v1.0.2")
    print("=" * 60)

    assert installer_exe.is_file(), f"Installer {installer_exe} not found!"
    assert db_path.is_file(), f"Target database {db_path} not found!"

    # 1. Pre-upgrade state snapshot
    print("\n1. Capturing pre-upgrade database state...")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    pre_counts = {}
    for table in ["users", "jobs", "user_applications", "companies", "contacts", "resumes"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            pre_counts[table] = cursor.fetchone()[0]
        except Exception as e:
            pre_counts[table] = str(e)
    conn.close()

    print("Pre-upgrade table counts:")
    for tbl, count in pre_counts.items():
        print(f"  - {tbl:<18}: {count}")

    assert pre_counts["jobs"] == 451, f"Expected 451 jobs, got {pre_counts['jobs']}"
    assert pre_counts["user_applications"] == 57, f"Expected 57 applications, got {pre_counts['user_applications']}"
    assert pre_counts["users"] >= 1, "Expected at least 1 user"

    ai_config_pre = None
    if ai_config_path.is_file():
        ai_config_pre = json.loads(ai_config_path.read_text(encoding="utf-8"))
        print(f"Pre-upgrade AI provider: {ai_config_pre.get('active_provider')}")

    # 2. Execute Inno Setup in-place upgrade silently
    print(f"\n2. Executing silent in-place upgrade with {installer_exe.name}...")
    cmd = [
        str(installer_exe),
        f"/DIR={install_target}",
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
    ]
    t0 = time.time()
    result = subprocess.run(cmd, check=True)
    duration = round(time.time() - t0, 2)
    print(f"[OK] In-place upgrade completed in {duration}s with exit code {result.returncode}.")

    # 3. Post-upgrade database integrity verification
    print("\n3. Verifying post-upgrade data persistence in %LOCALAPPDATA%\\Compust...")
    assert db_path.is_file(), "CRITICAL: Database file missing after upgrade!"
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    post_counts = {}
    for table in ["users", "jobs", "user_applications", "companies", "contacts", "resumes"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        post_counts[table] = cursor.fetchone()[0]
    conn.close()

    print("Post-upgrade table counts:")
    for tbl, count in post_counts.items():
        print(f"  - {tbl:<18}: {count}")

    for tbl in ["users", "jobs", "user_applications", "companies", "contacts", "resumes"]:
        assert post_counts[tbl] == pre_counts[tbl], (
            f"DATA CORRUPTION / LOSS in {tbl}: pre={pre_counts[tbl]}, post={post_counts[tbl]}"
        )
    print("[OK] All table row counts match pre-upgrade numbers with 100% fidelity.")

    if ai_config_pre:
        assert ai_config_path.is_file(), "AI config file missing after upgrade!"
        ai_config_post = json.loads(ai_config_path.read_text(encoding="utf-8"))
        assert ai_config_post.get("active_provider") == ai_config_pre.get("active_provider")
        print("[OK] AI config persisted with identical settings.")

    # 4. Check installation marker
    install_marker = install_target / ".install_complete"
    assert install_marker.is_file(), "Installation marker .install_complete missing!"
    marker_text = install_marker.read_text(encoding="utf-8")
    print(f"Installed marker content:\n{marker_text.strip()}")
    assert "version=1.0.2" in marker_text, f"Expected version=1.0.2 in marker, got {marker_text}"

    # 5. Start upgraded backend service and test live endpoints
    print("\n4. Starting upgraded Compust backend service from A:\\Compust...")
    backend_py = install_target / "runtime" / "python.exe"
    launcher_py = install_target / "launcher" / "launcher_core.py"
    
    proc = subprocess.Popen(
        [str(backend_py), str(launcher_py), "--mode=installed", "--no-tray"],
        cwd=str(install_target),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        # Poll health endpoint
        print("Polling http://127.0.0.1:8000/health...")
        healthy = False
        health_data = {}
        for attempt in range(25):
            time.sleep(1.0)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2.0) as resp:
                    if resp.status == 200:
                        health_data = json.loads(resp.read().decode())
                        healthy = True
                        break
            except Exception:
                pass

        assert healthy, "Upgraded backend failed to respond at /health within 25 seconds!"
        print("[OK] Backend is healthy:")
        print(f"  - App: {health_data.get('app')}")
        print(f"  - Version: {health_data.get('version')}")
        print(f"  - Mode: {health_data.get('mode')}")
        print(f"  - Database: {health_data.get('database')}")
        print(f"  - Latency: {health_data.get('latency_ms')} ms")
        assert health_data.get("version") == "1.0.2", f"Expected version 1.0.2, got {health_data.get('version')}"

        # Verify live jobs endpoint
        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/jobs?page=1&page_size=5&active_only=false", timeout=3.0) as resp:
            assert resp.status == 200
            jobs_data = json.loads(resp.read().decode())
            print(f"[OK] Live /api/v1/jobs?active_only=false returned {jobs_data.get('total')} total jobs.")
            assert jobs_data.get("total") == 451, f"Expected 451 total jobs, got {jobs_data.get('total')}"

        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/jobs?page=1&page_size=5", timeout=3.0) as resp:
            assert resp.status == 200
            active_jobs_data = json.loads(resp.read().decode())
            print(f"[OK] Live /api/v1/jobs (active_only=true) returned {active_jobs_data.get('total')} active jobs.")
            assert active_jobs_data.get("total") == 412, f"Expected 412 active jobs, got {active_jobs_data.get('total')}"

        # Verify live data management sources endpoint
        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/data/import/sources", timeout=3.0) as resp:
            assert resp.status == 200
            dm_data = json.loads(resp.read().decode())
            target_stats = dm_data.get("target_stats", {})
            print(f"[OK] Target stats from API: {target_stats}")
            assert target_stats.get("jobs") == 451
            assert target_stats.get("user_applications") == 57

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    print("\n" + "=" * 60)
    print("[SUCCESS] IN-PLACE UPGRADE TEST PASSED WITH 100% DATA PRESERVATION!")
    print("=" * 60)

if __name__ == "__main__":
    test_inplace_upgrade()
