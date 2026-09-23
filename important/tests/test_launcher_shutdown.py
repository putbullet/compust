import os
import sys
import subprocess
import time
import pytest
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

from launcher.launcher_core import (
    prompt_shutdown_confirmation,
    terminate_compust_services,
    free_ports,
    kill_process_tree,
    find_repo_root,
    _SPAWNED_PROCESSES,
)


def test_shutdown_confirmation_timeout_defaults_to_safe_shutdown(monkeypatch):
    """Assert that if the user does not respond within timeout, it defaults to safe shutdown (True)."""
    start = time.time()
    result = prompt_shutdown_confirmation(timeout_seconds=1)
    duration = time.time() - start

    assert result is True
    assert duration >= 1.0


def test_shutdown_confirmation_user_answers_yes(monkeypatch):
    """Assert that answering 'y' confirms shutdown (returns True)."""
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO("y\n"))
    result = prompt_shutdown_confirmation(timeout_seconds=2)
    assert result is True


def test_shutdown_confirmation_user_answers_no(monkeypatch):
    """Assert that answering 'n' cancels shutdown (returns False)."""
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO("n\n"))
    result = prompt_shutdown_confirmation(timeout_seconds=2)
    assert result is False


def test_shutdown_confirmation_user_answers_enter(monkeypatch):
    """Assert that pressing Enter (empty input) cancels shutdown (returns False)."""
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO("\n"))
    result = prompt_shutdown_confirmation(timeout_seconds=2)
    assert result is False


def _get_free_port() -> int:
    """Find a random unused ephemeral port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_free_ports_terminates_listening_processes():
    """Verify that free_ports discovers and terminates the target process on a throwaway port,

    while leaving unrelated processes on other ports untouched.
    Uses psutil exclusively -- no shell=True, no findstr, no netstat.
    """
    import psutil

    target_port = _get_free_port()
    unrelated_port = _get_free_port()
    while unrelated_port == target_port:
        unrelated_port = _get_free_port()

    # Listener code running a simple HTTP server on the specified port
    code_target = f"import http.server, socketserver; socketserver.TCPServer(('127.0.0.1', {target_port}), http.server.SimpleHTTPRequestHandler).serve_forever()"
    code_unrelated = f"import http.server, socketserver; socketserver.TCPServer(('127.0.0.1', {unrelated_port}), http.server.SimpleHTTPRequestHandler).serve_forever()"

    target_proc = subprocess.Popen(
        [sys.executable, "-c", code_target],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    unrelated_proc = subprocess.Popen(
        [sys.executable, "-c", code_unrelated],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Helper to get all PIDs associated with a subprocess (parent + children)
        def get_proc_pids(proc):
            try:
                p = psutil.Process(proc.pid)
                return {proc.pid} | {c.pid for c in p.children(recursive=True)}
            except psutil.NoSuchProcess:
                return {proc.pid}

        # Wait up to 5s for both listeners to be ready
        ready = False
        target_listen_pid = None
        unrelated_listen_pid = None
        for _ in range(50):
            target_pids = get_proc_pids(target_proc)
            unrelated_pids = get_proc_pids(unrelated_proc)

            for conn in psutil.net_connections(kind="tcp"):
                if conn.status == psutil.CONN_LISTEN:
                    if conn.laddr.port == target_port and conn.pid in target_pids:
                        target_listen_pid = conn.pid
                    if conn.laddr.port == unrelated_port and conn.pid in unrelated_pids:
                        unrelated_listen_pid = conn.pid

            if target_listen_pid and unrelated_listen_pid:
                ready = True
                break
            time.sleep(0.1)

        assert ready, f"Test listeners did not bind to ports {target_port} and {unrelated_port} in time"

        # Verify target and unrelated processes are expected python processes before killing
        assert target_proc.poll() is None, "Target test listener died prematurely"
        assert unrelated_proc.poll() is None, "Unrelated test listener died prematurely"
        assert "python" in psutil.Process(target_listen_pid).name().lower()
        assert "python" in psutil.Process(unrelated_listen_pid).name().lower()

        # Call free_ports ONLY on the target_port
        free_ports([target_port])
        time.sleep(0.5)

        # Assert (a): Target listener PID was terminated and port freed
        assert not psutil.pid_exists(target_listen_pid), (
            f"Target listening PID {target_listen_pid} on port {target_port} was not terminated"
        )

        # Assert (b): Unrelated process on other port is UNTOUCHED and still running
        assert unrelated_proc.poll() is None, (
            f"Unrelated process PID {unrelated_proc.pid} on port {unrelated_port} was unexpectedly killed!"
        )
        assert psutil.pid_exists(unrelated_listen_pid), "Unrelated listening PID does not exist"

    finally:
        for p in [target_proc, unrelated_proc]:
            try:
                if p.poll() is None:
                    p.terminate()
                    p.wait(timeout=2)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass


def test_terminate_compust_services_cleans_tracked_processes_and_pids(tmp_path):
    """Assert terminate_compust_services terminates spawned procs and removes pid markers."""
    dummy_proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _SPAWNED_PROCESSES.append(("TestService", dummy_proc))

    repo_dir = find_repo_root()
    pid_file = repo_dir / ".compust_pids.json"
    pid_file.write_text(f'{{"test": {dummy_proc.pid}}}', encoding="utf-8")

    terminate_compust_services(repo_dir)

    assert not pid_file.exists()
    assert dummy_proc.poll() is not None
