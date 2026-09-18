"""Automated test suite for Compust One-Click Windows Launcher."""

import json
import os
import socket
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add repository root to sys.path to import launcher modules
import sys
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "launcher") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "launcher"))

from launcher.launcher_core import (
    find_repo_root,
    get_configured_db_host_port,
    is_tcp_port_open,
    is_http_alive,
    load_tracked_pids,
    save_tracked_pids,
    is_process_running,
    ensure_mysql_running,
    ensure_backend_running,
    ensure_frontend_running,
    launch_compust,
)


def test_find_repo_root():
    """Verify dynamic path resolution finds repository root containing 'important'."""
    root = find_repo_root()
    assert (root / "important").is_dir()
    assert (root / "launcher").is_dir()


def test_get_configured_db_host_port():
    """Verify database host and port extraction with custom and default URLs."""
    with patch.dict(os.environ, {"COMPUST_DATABASE_URL": "mysql+pymysql://user:pass@127.0.0.1:3308/compust"}):
        host, port = get_configured_db_host_port(REPO_ROOT)
        assert host == "127.0.0.1"
        assert port == 3308

    with patch.dict(os.environ, {}, clear=True):
        host, port = get_configured_db_host_port(REPO_ROOT)
        assert isinstance(host, str)
        assert isinstance(port, int)


def test_is_tcp_port_open_with_live_socket():
    """Verify is_tcp_port_open detects active listening sockets and closed ports."""
    # Bind an ephemeral port
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    try:
        assert is_tcp_port_open("127.0.0.1", port, timeout=0.5) is True
    finally:
        srv.close()

    # Once closed, should report False
    assert is_tcp_port_open("127.0.0.1", port, timeout=0.2) is False


def test_tracked_pids_persistence(tmp_path):
    """Verify PID tracking file saves and reloads safely."""
    pids = {"backend": 1234, "frontend": 5678}
    save_tracked_pids(tmp_path, pids)

    loaded = load_tracked_pids(tmp_path)
    assert loaded == pids


def test_is_process_running_current_process():
    """Verify is_process_running returns True for current PID and False for non-existent."""
    assert is_process_running(os.getpid()) is True
    assert is_process_running(99999999) is False
    assert is_process_running(0) is False


def test_ensure_mysql_running_when_port_open():
    """Verify MySQL check returns True immediately if port is open."""
    with patch("launcher.launcher_core.is_tcp_port_open", return_value=True):
        res = ensure_mysql_running(REPO_ROOT, port=3306)
        assert res is True


def test_ensure_mysql_running_when_unavailable():
    """Verify MySQL check gracefully returns False if port is closed and no XAMPP found."""
    with patch("launcher.launcher_core.is_tcp_port_open", return_value=False), \
         patch("launcher.launcher_core.find_xampp_directory", return_value=None):
        res = ensure_mysql_running(REPO_ROOT, port=3306)
        assert res is False


def test_ensure_backend_running_already_alive():
    """Verify backend check does not spawn duplicate processes if already alive."""
    with patch("launcher.launcher_core.is_http_alive", return_value=True), \
         patch("subprocess.Popen") as mock_popen:
        res = ensure_backend_running(REPO_ROOT, port=8000)
        assert res is True
        mock_popen.assert_not_called()


def test_ensure_frontend_running_already_alive():
    """Verify frontend check does not spawn duplicate processes if already alive."""
    with patch("launcher.launcher_core.is_http_alive", return_value=True), \
         patch("subprocess.Popen") as mock_popen:
        res, url = ensure_frontend_running(REPO_ROOT, port=5173)
        assert res is True
        assert url == "http://127.0.0.1:5173"
        mock_popen.assert_not_called()


def test_duplicate_prevention_in_launch():
    """Verify launch_compust prevents duplicate instances and opens browser if already running."""
    with patch("launcher.launcher_core.is_http_alive", return_value=True), \
         patch("webbrowser.open") as mock_browser, \
         patch("launcher.launcher_core.ensure_mysql_running") as mock_mysql, \
         patch("launcher.launcher_core.ensure_backend_running") as mock_backend:

        code = launch_compust()
        assert code == 0
        mock_browser.assert_called_once_with("http://127.0.0.1:5173")
        # Should not have attempted to start MySQL or backend
        mock_mysql.assert_not_called()
        mock_backend.assert_not_called()
