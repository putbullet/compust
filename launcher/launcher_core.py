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
import psutil
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
                    stdin=subprocess.DEVNULL,
                )
            elif mysqld_exe.exists():
                logger.info(f"Launching MySQL via {mysqld_exe}...")
                subprocess.Popen(
                    [str(mysqld_exe), "--console"],
                    cwd=str(xampp_dir / "mysql"),
                    creationflags=creation_flags,
                    stdin=subprocess.DEVNULL,
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

    creation_flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0

    cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "src.app.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--reload",
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(important_dir),
            creationflags=creation_flags,
            stdin=subprocess.DEVNULL,
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


def ensure_frontend_running(repo_root: Path, host: str = "127.0.0.1", port: int = 5173) -> tuple[bool, str]:
    """
    Ensure React frontend is available.
    Supports either:
    1. Standalone production mode: FastAPI backend serves compiled frontend/dist directly at port 8000.
    2. Developer mode: Vite dev server running on port 5173 via npm.
    """
    # Check if developer Vite dev server is already running
    frontend_dev_url = f"http://{host}:{port}"
    if is_http_alive(frontend_dev_url):
        logger.info("Vite React development server is already active on port 5173.")
        return True, frontend_dev_url

    # Check if compiled production build exists
    dist_index = repo_root / "important" / "frontend" / "dist" / "index.html"
    has_npm = False
    try:
        npm_probe = "where npm" if os.name == "nt" else "which npm"
        subprocess.check_output(npm_probe, shell=True, stderr=subprocess.DEVNULL)
        has_npm = True
    except Exception:
        has_npm = False

    if dist_index.is_file() and not has_npm:
        logger.info("Compiled production frontend (dist) detected and Node.js is not installed.")
        logger.info("FastAPI backend serves the application directly on port 8000.")
        return True, f"http://{host}:8000"

    # If Node.js / npm is available, start Vite dev server
    if has_npm:
        logger.info("Starting React frontend development server (npm run dev)...")
        frontend_dir = repo_root / "important" / "frontend"
        logs_dir = repo_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        frontend_log_file = open(logs_dir / "frontend.log", "a", encoding="utf-8")

        creation_flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

        try:
            proc = subprocess.Popen(
                [npm_cmd, "run", "dev"],
                cwd=str(frontend_dir),
                creationflags=creation_flags,
                shell=True if os.name == "nt" else False,
                stdin=subprocess.DEVNULL,
                stdout=frontend_log_file,
                stderr=frontend_log_file,
            )
            _SPAWNED_PROCESSES.append(("Frontend", proc))
            pids = load_tracked_pids(repo_root)
            pids["frontend"] = proc.pid
            save_tracked_pids(repo_root, pids)
            logger.info(f"Spawned frontend dev process (PID: {proc.pid}). Waiting for ready check...")

            # Poll frontend for up to 20 seconds
            for _ in range(40):
                time.sleep(0.5)
                if is_http_alive(frontend_dev_url):
                    logger.info(f"Frontend is ready and responsive at {frontend_dev_url}.")
                    return True, frontend_dev_url
                if proc.poll() is not None:
                    logger.warning(f"Frontend dev process ended (code {proc.returncode}). Checking for dist fallback...")
                    break

        except Exception as exc:
            logger.warning(f"Could not start npm dev server: {exc}")

    # Fallback to backend serving dist if available
    if dist_index.is_file():
        logger.info("Using compiled production frontend served by backend at port 8000.")
        return True, f"http://{host}:8000"

    logger.error("Neither Vite dev server nor compiled dist build is available. Check logs/frontend.log.")
    return False, ""
def kill_process_tree(pid: int) -> None:
    """Terminate a process and all its children cleanly."""
    if pid <= 4:
        return
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        parent.terminate()
        _, alive = psutil.wait_procs(children + [parent], timeout=3)
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    except Exception as exc:
        logger.warning(f"Error terminating process tree for PID {pid}: {exc}")



import psutil

def free_ports(ports: list[int] = [8000, 5173]) -> None:
    """Ensure specified ports are freed by terminating lingering listening processes."""
    if os.name != "nt":
        return

    for port in ports:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                pid = conn.pid
                if pid and pid > 4:
                    try:
                        proc = psutil.Process(pid)
                        logger.info(f"Port {port} held by PID {pid} ({proc.name()}). Terminating.")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                        logger.warning(f"Could not terminate PID {pid} on port {port}: {exc}")

def prompt_shutdown_confirmation(timeout_seconds: int = 10) -> bool:
    """Prompt user for confirmation (Y/N) to terminate Compust services.

    Y/y -> Proceed with shutdown
    N/n or Enter -> Cancel and continue running
    Timeout -> Proceed with shutdown (safe action to prevent orphaned processes holding ports)
    """
    prompt_msg = (
        f"\nReceived shutdown signal (Ctrl+C).\n"
        f"Are you sure you want to stop Compust services? (Y/N) "
        f"[Proceeding automatically in {timeout_seconds}s]: "
    )
    sys.stdout.write(prompt_msg)
    sys.stdout.flush()

    if os.name == "nt" and sys.stdin.isatty():
        import msvcrt
        # Drain any residual characters in the console input buffer
        while msvcrt.kbhit():
            msvcrt.getwch()

        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout_seconds:
                sys.stdout.write(f"\n[TIMEOUT] No response within {timeout_seconds}s. Proceeding with safe shutdown.\n")
                sys.stdout.flush()
                logger.info(f"Shutdown confirmation timed out after {timeout_seconds}s. Proceeding with safe shutdown.")
                return True

            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch.lower() == "y":
                    sys.stdout.write(f"{ch}\n")
                    sys.stdout.flush()
                    logger.info("User confirmed shutdown (Y).")
                    return True
                elif ch.lower() == "n":
                    sys.stdout.write(f"{ch}\n")
                    sys.stdout.flush()
                    logger.info("User cancelled shutdown (N).")
                    return False
                elif ch in ("\r", "\n"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    logger.info("User pressed Enter. Defaulting to cancel.")
                    return False
                elif ch == "\x03":  # Second Ctrl+C pressed
                    sys.stdout.write("\n[FORCED] Second Ctrl+C received. Forcing immediate shutdown.\n")
                    sys.stdout.flush()
                    logger.info("Forced shutdown requested by user (second Ctrl+C).")
                    return True

            time.sleep(0.05)
    else:
        import queue
        import threading

        input_queue: queue.Queue[str] = queue.Queue()

        def _reader():
            try:
                line = sys.stdin.readline()
                input_queue.put(line)
            except Exception:
                pass

        t = threading.Thread(target=_reader, daemon=True)
        t.start()

        try:
            line = input_queue.get(timeout=timeout_seconds)
            ans = line.strip().lower()
            if ans.startswith("y"):
                logger.info("User confirmed shutdown (Y).")
                return True
            elif ans.startswith("n") or ans == "":
                logger.info(f"User cancelled shutdown (input: '{ans}').")
                return False
            else:
                logger.info(f"Unrecognized response '{ans}', defaulting to safe shutdown.")
                return True
        except queue.Empty:
            sys.stdout.write(f"\n[TIMEOUT] No response within {timeout_seconds}s. Proceeding with safe shutdown.\n")
            sys.stdout.flush()
            logger.info("Shutdown confirmation timed out. Defaulting to safe shutdown.")
            return True


def terminate_compust_services(repo_root: Path) -> None:
    """Terminate all backend and frontend processes, release ports, and clean PID tracking."""
    logger.info("Stopping Compust services...")
    # 1. Terminate tracked subprocesses
    for name, proc in _SPAWNED_PROCESSES:
        try:
            if proc.poll() is None:
                logger.info(f"Stopping {name} process (PID: {proc.pid})...")
                kill_process_tree(proc.pid)
        except Exception as exc:
            logger.warning(f"Could not terminate {name}: {exc}")

    # 2. Terminate PIDs loaded from pid file
    pids = load_tracked_pids(repo_root)
    for name, pid in pids.items():
        if pid > 4:
            kill_process_tree(pid)

    # 3. Clean pid file
    pid_file = get_pid_file(repo_root)
    if pid_file.exists():
        try:
            pid_file.unlink()
        except Exception:
            pass

    # 4. Release ports 8000 and 5173
    free_ports([8000, 5173])
    logger.info("Compust shutdown complete. Ports 8000 and 5173 released.")


def check_extension_onboarding(repo_root: Path) -> None:
    """Check if Compust Capture browser extension onboarding has been presented.

    If first run, display clear dev/unpacked installation instructions for detected browsers.
    Subsequent runs are a fast no-op via local marker file.
    """
    marker = repo_root / "logs" / ".extension_onboarding_done"
    chrome_manifest = repo_root / "important" / "extension" / "dist" / "chrome" / "manifest.json"
    firefox_manifest = repo_root / "important" / "extension" / "dist" / "firefox" / "manifest.json"

    # Fast no-op if already completed and builds exist
    if marker.is_file() and (chrome_manifest.is_file() or firefox_manifest.is_file()):
        return

    # Detect installed browsers
    detected_browsers = []
    if os.name == "nt":
        browser_checks = [
            ("Google Chrome", [
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google\\Chrome\\Application\\chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google\\Chrome\\Application\\chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google\\Chrome\\Application\\chrome.exe",
            ]),
            ("Microsoft Edge", [
                Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Microsoft\\Edge\\Application\\msedge.exe",
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Microsoft\\Edge\\Application\\msedge.exe",
            ]),
            ("Brave Browser", [
                Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            ]),
            ("Mozilla Firefox", [
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Mozilla Firefox\\firefox.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Mozilla Firefox\\firefox.exe",
            ]),
        ]
        for b_name, paths in browser_checks:
            if any(p.is_file() for p in paths):
                detected_browsers.append(b_name)

    chrome_dist = repo_root / "important" / "extension" / "dist" / "chrome"
    firefox_dist = repo_root / "important" / "extension" / "dist" / "firefox"

    logger.info("=" * 60)
    logger.info("[FIRST-RUN ONBOARDING] Compust Capture Browser Extension")
    logger.info("------------------------------------------------------------")
    if detected_browsers:
        logger.info(f"Detected browsers: {', '.join(detected_browsers)}")
    logger.info("To capture vacancies from LinkedIn, Indeed, Glassdoor & WTTJ:")
    logger.info("  1. Chromium browsers (Chrome, Edge, Brave):")
    logger.info("     - Navigate to chrome://extensions or edge://extensions")
    logger.info("     - Toggle 'Developer mode' ON (top-right)")
    logger.info(f"     - Click 'Load unpacked' and select:")
    logger.info(f"       {chrome_dist}")
    logger.info("  2. Mozilla Firefox:")
    logger.info("     - Navigate to about:debugging#/runtime/this-firefox")
    logger.info(f"     - Click 'Load Temporary Add-on...' and select:")
    logger.info(f"       {firefox_dist / 'manifest.json'}")
    logger.info("  (Note: Unpacked extensions require this developer load step")
    logger.info("   due to browser security boundaries. Web Store publishing")
    logger.info("   is the standard path for automated enterprise deployment.)")
    logger.info("=" * 60)

    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"completed_at={time.time()}\n", encoding="utf-8")
    except Exception:
        pass


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
    frontend_dev_url = "http://127.0.0.1:5173"
    backend_up = is_http_alive(backend_url)
    frontend_dev_up = is_http_alive(frontend_dev_url)

    if backend_up and frontend_dev_up:
        logger.info("All Compust services are already active and healthy.")
        logger.info("Preventing duplicate instances: Opening application in browser...")
        webbrowser.open(frontend_dev_url)
        logger.info("Browser opened. Launcher exiting cleanly.")
        return 0

    # 2. Detect & check configured database connection
    db_host, db_port = get_configured_db_host_port(repo_root)
    mysql_active = ensure_mysql_running(repo_root, host=db_host, port=db_port)
    if not mysql_active:
        logger.info("MySQL service is not running. Compust will automatically utilize the embedded SQLite database.")

    # 3. Ensure Backend is running
    backend_ok = backend_up or ensure_backend_running(repo_root, host="127.0.0.1", port=8000)
    if not backend_ok:
        logger.error("FastAPI backend failed to start. Aborting launch. Check logs/backend.log.")
        return 1

    # 4. Ensure Frontend is available (either dev server or production dist)
    frontend_ok, target_url = ensure_frontend_running(repo_root, host="127.0.0.1", port=5173)

    if not frontend_ok or not target_url:
        logger.error("Frontend is unavailable. Aborting browser launch. Check logs/frontend.log.")
        return 1

    # 5. Open browser
    logger.info(f"Opening browser at: {target_url}")
    webbrowser.open(target_url)
    logger.info("=" * 60)
    logger.info("Compust is now running successfully!")
    logger.info(f"  -> Frontend: {target_url}")
    logger.info(f"  -> Backend:  http://127.0.0.1:8000")
    logger.info(f"  -> API Docs: http://127.0.0.1:8000/docs")
    logger.info("Keep this window open while using Compust.")
    logger.info("Press Ctrl+C in this window to stop all services.")
    logger.info("=" * 60)

    # 6. Check extension onboarding status (fast no-op on repeat launches)
    check_extension_onboarding(repo_root)

    if not keep_alive or "pytest" in sys.modules:
        return 0

    while True:
        try:
            while True:
                time.sleep(1.0)
                for name, proc in _SPAWNED_PROCESSES:
                    if proc.poll() is not None:
                        logger.warning(f"{name} process ended unexpectedly (code {proc.returncode}).")
        except KeyboardInterrupt:
            confirmed = prompt_shutdown_confirmation(timeout_seconds=10)
            if confirmed:
                terminate_compust_services(repo_root)
                return 0
            else:
                logger.info("Resuming Compust services. Press Ctrl+C in this window to stop.")
                continue


if __name__ == "__main__":
    sys.exit(launch_compust())
