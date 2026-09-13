"""Compust Windows One-Click Launcher Core Engine.

Handles:
- Dynamic root path resolution (no hardcoded directories)
- MySQL / XAMPP status check and safe auto-startup
- FastAPI backend lifecycle check and startup
- Vite frontend lifecycle check and startup
- Duplicate instance prevention
- Process tracking via .compust_pids.json
- Clean, sanitized logging to logs/launcher.log
- Automatic browser opening
"""

import json
import logging
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any


logger = logging.getLogger("compust.launcher")


def find_repo_root() -> Path:
    """Dynamically resolve the Compust repository root from current file location."""
    # Priority 1: Relative to this file
    current = Path(__file__).resolve().parent
    for candidate in [current.parent, current]:
        if (candidate / "important").is_dir():
            return candidate

    # Priority 2: Walk up directory tree
    probe = Path(__file__).resolve().parent
    while probe.parent != probe:
        if (probe / "important").is_dir():
            return probe
        probe = probe.parent

    # Priority 3: Current working directory
    cwd = Path.cwd()
    if (cwd / "important").is_dir():
        return cwd
    if (cwd.parent / "important").is_dir():
        return cwd.parent

    raise RuntimeError("Could not locate Compust repository root containing 'important' folder.")


def setup_launcher_logging(repo_root: Path) -> logging.Logger:
    """Configure sanitized logging to logs/launcher.log."""
    logs_dir = repo_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "launcher.log"

    logger.setLevel(logging.INFO)
    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Also add console handler for terminal output
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


def is_tcp_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is open and accepting connections on IPv4 or dual-stack."""
    targets = [host]
    if host != "127.0.0.1":
        targets.append("127.0.0.1")
    if host != "localhost":
        targets.append("localhost")

    for h in targets:
        try:
            with socket.create_connection((h, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            continue
    return False


def is_http_alive(url: str, timeout: float = 2.0) -> bool:
    """Check if an HTTP endpoint returns a healthy HTTP status code."""
    targets = [url]
    if "127.0.0.1" in url:
        targets.append(url.replace("127.0.0.1", "localhost"))
    elif "localhost" in url:
        targets.append(url.replace("localhost", "127.0.0.1"))

    for target_url in targets:
        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "CompustLauncher/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= resp.status < 400:
                    return True
        except Exception:
            continue
    return False


def get_pid_file(repo_root: Path) -> Path:
    return repo_root / ".compust_pids.json"


def load_tracked_pids(repo_root: Path) -> dict[str, int]:
    pid_file = get_pid_file(repo_root)
    if not pid_file.exists():
        return {}
    try:
        with open(pid_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {k: int(v) for k, v in data.items() if isinstance(v, (int, str)) and str(v).isdigit()}
    except Exception:
        return {}


def save_tracked_pids(repo_root: Path, pids: dict[str, int]) -> None:
    pid_file = get_pid_file(repo_root)
    try:
        with open(pid_file, "w", encoding="utf-8") as f:
            json.dump(pids, f, indent=2)
    except Exception as exc:
        logger.warning(f"Could not save tracked PIDs: {exc}")


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is currently active."""
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            # On Windows, tasklist check or kernel32 OpenProcess
            cmd = f'tasklist /FI "PID eq {pid}" /NH'
            out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            return str(pid) in out
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def find_xampp_directory(repo_root: Path) -> Path | None:
    """Check common installation locations for XAMPP."""
    candidates = [
        os.environ.get("XAMPP_HOME"),
        "C:\\xampp",
        "D:\\xampp",
        "E:\\xampp",
        "F:\\xampp",
    ]
    try:
        drive = repo_root.drive
        if drive:
            candidates.append(f"{drive}\\xampp")
    except Exception:
        pass

    for cand in candidates:
        if cand and Path(cand).is_dir():
            return Path(cand)
def get_configured_db_host_port(repo_root: Path) -> tuple[str, int]:
    """Parse configured database host and port dynamically from environment or important/.env."""
    host = "127.0.0.1"
    port = 3306

    # 1. Check direct environment variables
    db_url = os.environ.get("COMPUST_DATABASE_URL") or os.environ.get("DATABASE_URL")

    # 2. Check important/.env or .env file if available
    if not db_url:
        for env_path in [repo_root / "important" / ".env", repo_root / ".env"]:
            if env_path.is_file():
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            if line.startswith("COMPUST_DATABASE_URL=") or line.startswith("DATABASE_URL="):
                                db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                                break
                            if line.startswith("COMPUST_DATABASE_PORT=") or line.startswith("DB_PORT="):
                                p_str = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if p_str.isdigit():
                                    port = int(p_str)
                except Exception:
                    pass
            if db_url:
                break

    # 3. Parse host and port from database connection string if present
    if db_url:
        try:
            # Example: mysql+pymysql://root:pass@127.0.0.1:3306/compust
            if "@" in db_url:
                after_at = db_url.split("@", 1)[1]
                host_port = after_at.split("/", 1)[0]
                if ":" in host_port:
                    h, p = host_port.split(":", 1)
                    if h:
                        host = h
                    if p.isdigit():
                        port = int(p)
                elif host_port:
                    host = host_port
        except Exception:
            pass

    return host, port


def ensure_mysql_running(repo_root: Path, host: str = "127.0.0.1", port: int = 3306) -> bool:
    """Verify MySQL availability, attempting XAMPP auto-start if necessary."""
    logger.info(f"Checking MySQL status on {host}:{port}...")
    if is_tcp_port_open(host, port):
        logger.info(f"MySQL is actively running on {host}:{port}.")
        return True

    logger.warning(f"MySQL is NOT reachable on {host}:{port}. Attempting to locate XAMPP...")
    xampp_dir = find_xampp_directory(repo_root)

    if xampp_dir:
        logger.info(f"Found XAMPP directory at: {xampp_dir}")
        # Look for mysql_start.bat or mysqld.exe
        mysql_start_bat = xampp_dir / "mysql_start.bat"
        mysqld_exe = xampp_dir / "mysql" / "bin" / "mysqld.exe"

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        try:
            if mysql_start_bat.exists():
                logger.info(f"Launching MySQL via {mysql_start_bat}...")
                subprocess.Popen(
                    [str(mysql_start_bat)],
                    cwd=str(xampp_dir),
                    creationflags=creation_flags,
                    shell=True,
                )
            elif mysqld_exe.exists():
                logger.info(f"Launching MySQL via {mysqld_exe}...")
                subprocess.Popen(
                    [str(mysqld_exe), "--console"],
                    cwd=str(xampp_dir / "mysql"),
                    creationflags=creation_flags,
                )

            # Wait up to 10 seconds for MySQL to bind to port
            for attempt in range(1, 11):
                time.sleep(1.0)
                if is_tcp_port_open(host, port):
                    logger.info(f"MySQL successfully started and is now accepting connections on port {port} (attempt {attempt}).")
                    return True
        except Exception as exc:
            logger.error(f"Failed to auto-launch MySQL from XAMPP: {exc}")

    logger.warning(
        f"MySQL could not be automatically started on port {port}. "
        "Compust backend will start in resilient mode, but database features may be degraded until MySQL is started."
    )
    return False


def get_python_executable(repo_root: Path) -> str:
    """Resolve python executable, prioritizing the project's virtual environment."""
    venv_python_win = repo_root / "important" / ".venv" / "Scripts" / "python.exe"
    if venv_python_win.exists():
        return str(venv_python_win)

    venv_python_unix = repo_root / "important" / ".venv" / "bin" / "python"
    if venv_python_unix.exists():
        return str(venv_python_unix)

    return sys.executable


_SPAWNED_PROCESSES: list[tuple[str, subprocess.Popen]] = []


def ensure_backend_running(repo_root: Path, host: str = "127.0.0.1", port: int = 8000) -> bool:
    """Ensure FastAPI backend is running and healthy."""
    health_url = f"http://{host}:{port}/health"
    logger.info(f"Checking backend status at {health_url}...")

    if is_http_alive(health_url):
        logger.info("FastAPI backend is already alive and responding.")
        return True

    logger.info("Starting FastAPI backend service...")
    python_exe = get_python_executable(repo_root)
    important_dir = repo_root / "important"
    logs_dir = repo_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    backend_log_file = open(logs_dir / "backend.log", "a", encoding="utf-8")

    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "src.app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(important_dir),
            creationflags=creation_flags,
            stdout=backend_log_file,
            stderr=backend_log_file,
        )
        _SPAWNED_PROCESSES.append(("Backend", proc))
        pids = load_tracked_pids(repo_root)
        pids["backend"] = proc.pid
        save_tracked_pids(repo_root, pids)
        logger.info(f"Spawned backend process (PID: {proc.pid}). Waiting for health check...")

        # Poll health check for up to 15 seconds
        for _ in range(30):
            time.sleep(0.5)
            if is_http_alive(health_url):
                logger.info(f"Backend is ready and responsive at {health_url}.")
                return True
            if proc.poll() is not None:
                logger.error(f"Backend process terminated unexpectedly (code {proc.returncode}). See logs/backend.log")
                return False

        logger.warning("Backend did not respond to health check within 15 seconds. Check logs/backend.log")
        return False
    except Exception as exc:
        logger.error(f"Failed to start FastAPI backend: {exc}")
        return False


def ensure_frontend_running(repo_root: Path, host: str = "127.0.0.1", port: int = 5173) -> bool:
    """Ensure Vite React frontend is running."""
    frontend_url = f"http://{host}:{port}"
    logger.info(f"Checking frontend status at {frontend_url}...")

    if is_http_alive(frontend_url):
        logger.info("React frontend is already alive and responding.")
        return True

    logger.info("Starting React frontend development server...")
    frontend_dir = repo_root / "important" / "frontend"
    logs_dir = repo_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    frontend_log_file = open(logs_dir / "frontend.log", "a", encoding="utf-8")

    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

    try:
        proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=str(frontend_dir),
            creationflags=creation_flags,
            shell=True if os.name == "nt" else False,
            stdout=frontend_log_file,
            stderr=frontend_log_file,
        )
        _SPAWNED_PROCESSES.append(("Frontend", proc))
        pids = load_tracked_pids(repo_root)
        pids["frontend"] = proc.pid
        save_tracked_pids(repo_root, pids)
        logger.info(f"Spawned frontend process (PID: {proc.pid}). Waiting for ready check...")

        # Poll frontend for up to 20 seconds
        for _ in range(40):
            time.sleep(0.5)
            if is_http_alive(frontend_url):
                logger.info(f"Frontend is ready and responsive at {frontend_url}.")
                return True
            if proc.poll() is not None:
                logger.error(f"Frontend process terminated unexpectedly (code {proc.returncode}). See logs/frontend.log")
                return False

        logger.warning("Frontend did not respond within 20 seconds. Check logs/frontend.log")
        return False
    except Exception as exc:
        logger.error(f"Failed to start frontend dev server: {exc}")
        return False


def launch_compust(keep_alive: bool = True) -> int:
    """Main one-click launch procedure."""
    try:
        repo_root = find_repo_root()
    except Exception as exc:
        print(f"FATAL: {exc}")
        return 1

    setup_launcher_logging(repo_root)
    logger.info("=" * 60)
    logger.info("Starting Compust One-Click Launcher...")
    logger.info(f"Repository Root: {repo_root}")

    # 1. Duplicate instance check
    backend_url = "http://127.0.0.1:8000/health"
    frontend_url = "http://127.0.0.1:5173"
    backend_up = is_http_alive(backend_url)
    frontend_up = is_http_alive(frontend_url)

    if backend_up and frontend_up:
        logger.info("All Compust services are already active and healthy.")
        logger.info("Preventing duplicate instances: Opening application in browser...")
        webbrowser.open(frontend_url)
        logger.info("Browser opened. Launcher exiting cleanly.")
        return 0

    # 2. Detect & check configured database connection first
    db_host, db_port = get_configured_db_host_port(repo_root)
    ensure_mysql_running(repo_root, host=db_host, port=db_port)

    # 3. Ensure Backend is running
    backend_ok = backend_up or ensure_backend_running(repo_root, host="127.0.0.1", port=8000)

    # 4. Ensure Frontend is running
    frontend_ok = frontend_up or ensure_frontend_running(repo_root, host="127.0.0.1", port=5173)

    if not frontend_ok:
        logger.error("Frontend service is unavailable. Aborting browser launch. Check logs/frontend.log.")
        return 1

    # 5. Open browser
    logger.info(f"Opening browser at: {frontend_url}")
    webbrowser.open(frontend_url)
    logger.info("=" * 60)
    logger.info("Compust is now running successfully!")
    logger.info(f"  -> Frontend: {frontend_url}")
    logger.info(f"  -> Backend:  http://127.0.0.1:8000")
    logger.info(f"  -> API Docs: http://127.0.0.1:8000/docs")
    logger.info("Keep this window open while using Compust.")
    logger.info("Press Ctrl+C in this window to stop all services.")
    logger.info("=" * 60)

    if not keep_alive or "pytest" in sys.modules:
        return 0

    try:
        while True:
            time.sleep(1.0)
            for name, proc in _SPAWNED_PROCESSES:
                if proc.poll() is not None:
                    logger.warning(f"{name} process ended unexpectedly (code {proc.returncode}).")
    except KeyboardInterrupt:
        logger.info("\nStopping Compust services...")
    finally:
        for name, proc in _SPAWNED_PROCESSES:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        logger.info("Compust shutdown complete.")

    return 0


if __name__ == "__main__":
    sys.exit(launch_compust())
