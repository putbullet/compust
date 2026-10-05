"""
Automated validation of Compust Self-Healing Check & Repair,
Dynamic Port Selection, and Diagnostic Report generation.
"""

import json
import socket
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "launcher") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "launcher"))

from launcher.launcher_core import (
    find_available_port,
    run_check_and_repair,
    create_diagnostic_report,
    get_user_logs_dir,
)


def test_find_available_port_increments_when_port_busy():
    """Verify find_available_port skips busy ports and selects first free port."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    busy_port = srv.getsockname()[1]

    try:
        chosen = find_available_port(start_port=busy_port, max_probes=10)
        assert chosen > busy_port
    finally:
        srv.close()


def test_run_check_and_repair_validates_repo_health():
    """Verify run_check_and_repair returns a structured dictionary with expected keys."""
    res = run_check_and_repair(REPO_ROOT)
    assert isinstance(res, dict)
    assert "status" in res
    assert "repairs_performed" in res
    assert "issues_detected" in res
    assert "ollama" in res
    assert isinstance(res["ollama"], dict)


def test_create_diagnostic_report_creates_valid_zip(tmp_path, monkeypatch):
    """Verify create_diagnostic_report creates a valid zip containing logs and system info."""
    monkeypatch.setenv("COMPUST_USER_DATA_DIR", str(tmp_path))

    logs_dir = get_user_logs_dir(REPO_ROOT)
    (logs_dir / "launcher.log").write_text("2026-10-04 [INFO] Sample launcher log\n", encoding="utf-8")
    (logs_dir / "backend.log").write_text("2026-10-04 [INFO] Sample backend log\n", encoding="utf-8")

    zip_path = create_diagnostic_report(REPO_ROOT)
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "system_info.json" in namelist
        assert "logs/launcher.log" in namelist
        assert "logs/backend.log" in namelist

        info_data = json.loads(zf.read("system_info.json").decode("utf-8"))
        assert "platform" in info_data
        assert "python_version" in info_data
