"""
Compust Windows One-Click Unified Launcher & Orchestrator.

One shared implementation used by both the installed Compust.exe launcher
and the developer shortcut.

Handles:
- Dynamic root path resolution (installed vs developer checkout)
- Mode detection ('installed' vs 'dev') with strict data & environment isolation
- Instance registry (%LOCALAPPDATA%\\Compust\\running_instances.json) & named mutex
- Single-instance prevention: focuses running instance if same data directory
- Stale instance and Compust-owned orphan cleanup (never kills foreign processes)
- Smart port selection: prefers 8000; selects next free port if occupied
- Exclusive, loopback-only binding (127.0.0.1 with SO_EXCLUSIVEADDRUSE on Windows)
- Dynamic port propagation to Vite reverse proxy and backend CORS settings
- Safe child process tracking and non-interactive, clean termination on exit/Ctrl+C/tray Quit
- Self-healing Check & Repair and Diagnostic Report generation
- System-tray menu integration (Open, Restart, Logs, Check & Repair, Quit)
"""

import atexit
import ctypes
import hashlib
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from typing import Any

import psutil

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger("compust.launcher")
APP_VERSION = "1.0.3"

# Global tracking for clean shutdown
_ACTIVE_CHILDREN: list[tuple[str, subprocess.Popen]] = []
_SPAWNED_PROCESSES = _ACTIVE_CHILDREN
_ACQUIRED_MUTEX_HANDLE: Any = None
_REGISTERED_INSTANCE: dict[str, Any] | None = None
_SHUTDOWN_PERFORMED = False


# ==============================================================================
# 1. Path & Mode Resolution
# ==============================================================================

def find_repo_root() -> Path:
    """Dynamically resolve the Compust root directory containing 'important'."""
    current = Path(__file__).resolve().parent
    for candidate in [current.parent, current]:
        if (candidate / "important").is_dir():
            return candidate.resolve()

    probe = Path(__file__).resolve().parent
    while probe.parent != probe:
        if (probe / "important").is_dir():
            return probe.resolve()
        probe = probe.parent

    cwd = Path.cwd().resolve()
    if (cwd / "important").is_dir():
        return cwd
    if (cwd.parent / "important").is_dir():
        return cwd.parent

    raise RuntimeError("Could not locate Compust root directory containing 'important' folder.")


def determine_mode(repo_root: Path) -> str:
    """
    Determine whether to run in 'installed' or 'dev' mode.
    Command-line flags override heuristics.
    """
    if "--mode=installed" in sys.argv or "--installed" in sys.argv:
        return "installed"
    if "--mode=dev" in sys.argv or "--dev" in sys.argv:
        return "dev"

    env_mode = os.environ.get("COMPUST_APP_MODE")
    if env_mode in ("installed", "dev"):
        return env_mode.lower()

    # Installed indicator: .install_complete marker exists and no .git folder
    if (repo_root / ".install_complete").is_file() and not (repo_root / ".git").exists():
        return "installed"

    return "dev"


def get_common_app_data_dir() -> Path:
    """Get the common per-user Compust directory (%LOCALAPPDATA%\\Compust)."""
    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA")
        base = Path(local_app) / "Compust" if local_app else Path.home() / "AppData" / "Local" / "Compust"
    else:
        base = Path.home() / ".compust"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_data_dir(repo_root: Path, mode: str) -> Path:
    """
    Resolve isolated data directory for this instance.
    - Installed mode: %LOCALAPPDATA%\\Compust
    - Dev mode: <repo_root>/important/data
    - Explicit override via COMPUST_USER_DATA_DIR respected
    """
    if os.environ.get("COMPUST_USER_DATA_DIR"):
        p = Path(os.environ["COMPUST_USER_DATA_DIR"]).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    if mode == "installed":
        p = get_common_app_data_dir()
    else:
        p = (repo_root / "important" / "data").resolve()

    p.mkdir(parents=True, exist_ok=True)
    return p


def get_logs_dir(data_dir: Path) -> Path:
    """Get logs directory inside data directory."""
    p = data_dir / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def setup_launcher_logging(data_dir: Path) -> logging.Logger:
    """Configure sanitized logging to logs/launcher.log."""
    logs_dir = get_logs_dir(data_dir)
    log_file = logs_dir / "launcher.log"

    logger.setLevel(logging.INFO)
    if not logger.handlers:
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


# ==============================================================================
# 2. Named Mutex & Registry Management
# ==============================================================================

def acquire_named_mutex(data_dir: Path) -> tuple[bool, Any]:
    """
    Acquire a Windows named mutex tied to the target data directory.
    Returns (acquired: bool, handle: Any).
    """
    if os.name != "nt":
        return True, None

    try:
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        CreateMutexW = kernel32.CreateMutexW
        CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        CreateMutexW.restype = wintypes.HANDLE
        GetLastError = kernel32.GetLastError
        ERROR_ALREADY_EXISTS = 183

        # Mutex name scoped to lowercase hash of data directory path
        hash_id = hashlib.md5(str(data_dir).lower().encode("utf-8")).hexdigest()
        mutex_name = f"Local\\Compust_Mutex_{hash_id}"

        handle = CreateMutexW(None, True, mutex_name)
        err = GetLastError()

        if handle and err == ERROR_ALREADY_EXISTS:
            return False, handle
        return bool(handle), handle
    except Exception as exc:
        logger.warning(f"Could not initialize Windows named mutex: {exc}")
        return True, None


def release_named_mutex(handle: Any) -> None:
    """Release a previously acquired Windows named mutex."""
    if os.name == "nt" and handle:
        try:
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL
            CloseHandle(handle)
        except Exception:
            pass


def get_registry_file() -> Path:
    """Central registry file tracking all active Compust instances on this user account."""
    common_dir = get_common_app_data_dir()
    return common_dir / "running_instances.json"


def query_health_identity(port: int, timeout: float = 0.8) -> dict[str, Any] | None:
    """Query /health on 127.0.0.1:<port> and return instance identity document if Compust."""
    url = f"http://127.0.0.1:{port}/health"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CompustLauncher/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and data.get("app") == "compust":
                    return data
    except Exception:
        pass
    return None


def is_pid_alive(pid: int) -> bool:
    """Check if a process with given PID is alive."""
    if pid <= 4:
        return False
    try:
        return psutil.pid_exists(pid)
    except Exception:
        return False


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is alive (compatibility alias)."""
    return is_pid_alive(pid)


def is_compust_process(pid: int) -> bool:
    """Verify if a process PID is legitimately a Compust backend/frontend process."""
    if not is_pid_alive(pid):
        return False
    try:
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline()).lower()
        if "compust" in cmdline or "main:app" in cmdline or "uvicorn" in cmdline or "vite" in cmdline:
            return True
    except Exception:
        pass
    return False


def load_instance_registry() -> list[dict[str, Any]]:
    """Load running instances list from the central registry file."""
    reg_file = get_registry_file()
    if not reg_file.is_file():
        return []
    try:
        data = json.loads(reg_file.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "instances" in data:
            return data["instances"]
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_instance_registry(instances: list[dict[str, Any]]) -> None:
    """Atomically write the instance registry."""
    reg_file = get_registry_file()
    try:
        tmp_file = reg_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps({"instances": instances}, indent=2), encoding="utf-8")
        tmp_file.replace(reg_file)
    except Exception as exc:
        logger.warning(f"Could not write instance registry: {exc}")


def clean_stale_registry_entries() -> list[dict[str, Any]]:
    """Remove dead or unresponsive instances from the registry, cleaning up orphans safely."""
    active = []
    for inst in load_instance_registry():
        pid = inst.get("pid")
        port = inst.get("port")
        if pid and is_pid_alive(pid):
            # Check if backend responds
            health = query_health_identity(port) if port else None
            if health and health.get("app") == "compust":
                active.append(inst)
                continue

        # If PID is dead or health failed, clean up any lingering child PIDs if Compust-owned
        backend_pid = inst.get("backend_pid")
        if backend_pid and is_compust_process(backend_pid):
            logger.info(f"Cleaning up orphaned Compust backend process (PID {backend_pid})...")
            kill_process_tree(backend_pid)

        frontend_pid = inst.get("frontend_pid")
        if frontend_pid and is_compust_process(frontend_pid):
            logger.info(f"Cleaning up orphaned Compust frontend process (PID {frontend_pid})...")
            kill_process_tree(frontend_pid)

    save_instance_registry(active)
    return active


def register_current_instance(entry: dict[str, Any]) -> None:
    """Register current running instance in the registry."""
    global _REGISTERED_INSTANCE
    _REGISTERED_INSTANCE = entry
    active = clean_stale_registry_entries()
    # Filter out any matching pid
    active = [i for i in active if i.get("pid") != entry.get("pid")]
    active.append(entry)
    save_instance_registry(active)


def unregister_current_instance() -> None:
    """Remove current instance from registry upon shutdown."""
    global _REGISTERED_INSTANCE
    if not _REGISTERED_INSTANCE:
        return
    cur_pid = os.getpid()
    active = [i for i in load_instance_registry() if i.get("pid") != cur_pid]
    save_instance_registry(active)
    _REGISTERED_INSTANCE = None


def load_tracked_pids(base_path: Path) -> dict[str, int]:
    """Load tracked PIDs from .compust_pids.json (compatibility helper)."""
    base = Path(base_path)
    pid_file = base / ".compust_pids.json" if base.is_dir() else base
    if pid_file.is_file():
        try:
            return json.loads(pid_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_tracked_pids(base_path: Path, pids: dict[str, int]) -> None:
    """Save tracked PIDs to .compust_pids.json (compatibility helper)."""
    base = Path(base_path)
    pid_file = base / ".compust_pids.json" if base.is_dir() else base
    pid_file.write_text(json.dumps(pids, indent=2), encoding="utf-8")


# ==============================================================================
# 3. Port Probing & Exclusive Loopback Binding
# ==============================================================================

def is_tcp_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if TCP port is open and accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def is_port_in_use_tcp(host: str, port: int) -> bool:
    """Test if a TCP port is currently open and accepting connections."""
    return is_tcp_port_open(host, port, timeout=0.3)


def is_http_alive(url: str, timeout: float = 2.0) -> bool:
    """Check if an HTTP endpoint is reachable and returns HTTP < 500."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CompustLauncher"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


def can_bind_exclusively(host: str, port: int) -> bool:
    """
    Test if we can bind exclusively to host:port with SO_EXCLUSIVEADDRUSE on Windows.
    Returns True if port is free and exclusively bindable, False otherwise.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        s.bind((host, port))
        s.listen(1)
        return True
    except OSError:
        return False
    finally:
        s.close()


def select_free_backend_port(
    target_data_dir: Path,
    mode: str,
    preferred_port: int = 8000,
    max_probes: int = 50,
) -> tuple[int, dict[str, Any] | None]:
    """
    Select an available port for the backend.
    - If preferred_port is occupied by another Compust instance:
      - If same data dir -> handled by caller (single-instance guard)
      - If different data dir -> selects next free port with clear user message
    - If preferred_port is occupied by a non-Compust program -> selects next free port
      without killing the foreign process!
    Returns (chosen_port, existing_compust_identity_if_any).
    """
    # 1. Check preferred port
    if not is_port_in_use_tcp("127.0.0.1", preferred_port) and can_bind_exclusively("127.0.0.1", preferred_port):
        return preferred_port, None

    # Port is occupied. Inspect what is running on it.
    health_ident = query_health_identity(preferred_port)

    if health_ident and health_ident.get("app") == "compust":
        other_mode = health_ident.get("mode", "unknown")
        other_pid = health_ident.get("pid", "?")
        other_data_dir = health_ident.get("data_dir", "")

        # Same data directory check is handled before calling this, but return identity
        if str(Path(other_data_dir).resolve()).lower() == str(target_data_dir.resolve()).lower():
            return preferred_port, health_ident

        logger.info(
            f"Port {preferred_port} is in use by another Compust instance "
            f"({other_mode}, PID {other_pid}) with data dir '{other_data_dir}'."
        )
    else:
        logger.info(f"Port {preferred_port} is occupied by another program.")

    # Find next free port
    for candidate in range(preferred_port + 1, preferred_port + 1 + max_probes):
        if not is_port_in_use_tcp("127.0.0.1", candidate) and can_bind_exclusively("127.0.0.1", candidate):
            if health_ident and health_ident.get("app") == "compust":
                logger.info(
                    f"Installed/Dev coexistence active: starting this {mode} instance on free port {candidate}."
                )
            else:
                logger.info(f"Auto-selected free port {candidate} for Compust backend.")
            return candidate, health_ident

    # Fallback to ephemeral port (port 0)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        assigned = s.getsockname()[1]
        logger.info(f"Auto-assigned ephemeral port {assigned}.")
        return assigned, health_ident


def select_free_frontend_port(preferred_port: int = 5173, max_probes: int = 25) -> int:
    """Find a free port for Vite frontend server in dev mode."""
    for p in range(preferred_port, preferred_port + max_probes):
        if not is_port_in_use_tcp("127.0.0.1", p) and can_bind_exclusively("127.0.0.1", p):
            return p
    return preferred_port


def find_available_port(start_port: int = 8000, max_probes: int = 50, host: str = "127.0.0.1") -> int:
    """Find first available and bindable TCP port (compatibility helper)."""
    for port in range(start_port, start_port + max_probes):
        if not is_tcp_port_open(host, port) and can_bind_exclusively(host, port):
            return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


# ==============================================================================
# 4. Process Lifecycle & Execution
# ==============================================================================

def get_python_executable(repo_root: Path) -> str:
    """Resolve Python executable prioritizing bundled runtime, then dev venv, then sys."""
    bundled_win = repo_root / "runtime" / "python.exe"
    if bundled_win.is_file():
        return str(bundled_win)

    venv_win = repo_root / "important" / ".venv" / "Scripts" / "python.exe"
    if venv_win.is_file():
        return str(venv_win)

    venv_unix = repo_root / "important" / ".venv" / "bin" / "python"
    if venv_unix.is_file():
        return str(venv_unix)

    return sys.executable


def build_backend_environment(repo_root: Path, mode: str, data_dir: Path, backend_port: int, frontend_port: int | None) -> dict[str, str]:
    """
    Construct an explicitly isolated or development environment for the backend subprocess.
    - Installed mode: filters out ambient COMPUST_* variables and DATABASE_URL.
    - Dev mode: preserves repo environment and allows loading important/.env.
    """
    if mode == "installed":
        # Start from base system env, stripping any ambient COMPUST_* or DATABASE_URL
        env = {
            k: v for k, v in os.environ.items()
            if not k.startswith("COMPUST_") and k != "DATABASE_URL"
        }
        env["COMPUST_APP_MODE"] = "installed"
        env["COMPUST_USER_DATA_DIR"] = str(data_dir)
        env["COMPUST_ACTIVE_PORT"] = str(backend_port)
        db_file = data_dir / "data" / "compust.db"
        db_file.parent.mkdir(parents=True, exist_ok=True)
        env["COMPUST_DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
        installed_origins = [
            f"http://127.0.0.1:{backend_port}",
            f"http://localhost:{backend_port}",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ]
        env["COMPUST_CORS_ALLOWED_ORIGINS"] = json.dumps(installed_origins)
        logger.info(f"Isolated runtime environment constructed for installed mode (data dir: {data_dir}).")
    else:
        env = os.environ.copy()
        env["COMPUST_APP_MODE"] = "dev"
        env["COMPUST_USER_DATA_DIR"] = str(data_dir)
        env["COMPUST_ACTIVE_PORT"] = str(backend_port)
        if frontend_port:
            origins = [
                f"http://127.0.0.1:{frontend_port}",
                f"http://localhost:{frontend_port}",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            ]
            env["COMPUST_CORS_ALLOWED_ORIGINS"] = json.dumps(origins)
        logger.info(f"Development environment constructed for dev mode (data dir: {data_dir}).")

    return env


def start_backend_service(
    repo_root: Path,
    mode: str,
    data_dir: Path,
    port: int,
    frontend_port: int | None = None,
) -> subprocess.Popen:
    """Launch the FastAPI backend service via dedicated exclusive server runner."""
    python_exe = get_python_executable(repo_root)
    important_dir = repo_root / "important"
    logs_dir = get_logs_dir(data_dir)
    backend_log = open(logs_dir / "backend.log", "a", encoding="utf-8")

    env = build_backend_environment(repo_root, mode, data_dir, port, frontend_port)

    creation_flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0

    # Priority 1: dedicated exclusive server runner (binds with SO_EXCLUSIVEADDRUSE)
    cmd = [
        python_exe,
        "-m",
        "src.app.server",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--mode",
        mode,
    ]

    logger.info(f"Starting Compust backend on 127.0.0.1:{port} (mode: {mode})...")
    proc = subprocess.Popen(
        cmd,
        cwd=str(important_dir),
        env=env,
        creationflags=creation_flags,
        stdin=subprocess.DEVNULL,
        stdout=backend_log,
        stderr=backend_log,
    )
    _ACTIVE_CHILDREN.append(("Backend", proc))
    return proc


def start_frontend_dev_service(
    repo_root: Path,
    data_dir: Path,
    backend_port: int,
    frontend_port: int,
) -> subprocess.Popen | None:
    """Start Vite React frontend in development mode."""
    frontend_dir = repo_root / "important" / "frontend"
    if not (frontend_dir / "package.json").is_file():
        logger.warning("frontend/package.json not found; skipping dev server startup.")
        return None

    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    logs_dir = get_logs_dir(data_dir)
    frontend_log = open(logs_dir / "frontend.log", "a", encoding="utf-8")

    env = os.environ.copy()
    env["VITE_PORT"] = str(frontend_port)
    env["VITE_BACKEND_PORT"] = str(backend_port)
    env["VITE_BACKEND_URL"] = f"http://127.0.0.1:{backend_port}"

    creation_flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0

    logger.info(f"Starting Vite React dev server on 127.0.0.1:{frontend_port} (proxying to backend {backend_port})...")
    try:
        proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=str(frontend_dir),
            env=env,
            creationflags=creation_flags,
            shell=True if os.name == "nt" else False,
            stdin=subprocess.DEVNULL,
            stdout=frontend_log,
            stderr=frontend_log,
        )
        _ACTIVE_CHILDREN.append(("Frontend", proc))
        return proc
    except Exception as exc:
        logger.error(f"Failed to launch Vite frontend dev server: {exc}")
        return None


def wait_for_service(url: str, timeout: float = 25.0) -> bool:
    """Poll URL until it responds with a healthy HTTP code or timeout occurs."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CompustLauncher"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if 200 <= resp.status < 400:
                    return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def kill_process_tree(pid: int) -> None:
    """Terminate a process and all its children cleanly without interactive prompts."""
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


def shutdown_services():
    """Non-interactive, clean termination of all tracked child processes and registry cleanup."""
    global _SHUTDOWN_PERFORMED
    if _SHUTDOWN_PERFORMED:
        return
    _SHUTDOWN_PERFORMED = True

    if not _ACTIVE_CHILDREN and not _REGISTERED_INSTANCE and not _ACQUIRED_MUTEX_HANDLE:
        return

    logger.info("Stopping Compust services cleanly...")
    for name, proc in _ACTIVE_CHILDREN:
        try:
            if proc.poll() is None:
                logger.info(f"Stopping {name} process (PID: {proc.pid})...")
                kill_process_tree(proc.pid)
        except Exception as exc:
            logger.warning(f"Could not stop {name}: {exc}")

    unregister_current_instance()

    if _ACQUIRED_MUTEX_HANDLE:
        release_named_mutex(_ACQUIRED_MUTEX_HANDLE)

    logger.info("Compust shutdown complete.")


# Register clean shutdown on normal Python termination
atexit.register(shutdown_services)


def install_signal_handlers():
    """Set up non-interactive signal handlers for Ctrl+C, SIGTERM, and Windows console events."""
    def handle_signal(sig, frame):
        logger.info(f"Received shutdown signal ({sig}). Exiting cleanly...")
        shutdown_services()
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
    except Exception:
        pass

    if os.name == "nt":
        try:
            # Register Windows Console Control Handler to trap console close / logoff
            kernel32 = ctypes.windll.kernel32
            HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

            def console_handler(ctrl_type):
                logger.info(f"Console control event received ({ctrl_type}). Cleaning up...")
                shutdown_services()
                return True

            _global_handler = HandlerRoutine(console_handler)
            kernel32.SetConsoleCtrlHandler(_global_handler, True)
        except Exception:
            pass


def prompt_shutdown_confirmation(timeout_seconds: int = 10) -> bool:
    """Prompt user for confirmation (Y/N) to terminate Compust services."""
    prompt_msg = (
        f"\nReceived shutdown signal (Ctrl+C).\n"
        f"Are you sure you want to stop Compust services? (Y/N) "
        f"[Proceeding automatically in {timeout_seconds}s]: "
    )
    sys.stdout.write(prompt_msg)
    sys.stdout.flush()

    if os.name == "nt" and sys.stdin.isatty():
        import msvcrt
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
                elif ch == "\x03":
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
                if line != "":  # Prevent EOF from resolving as empty user input
                    input_queue.put(line)
            except Exception:
                pass

        t = threading.Thread(target=_reader, daemon=True)
        t.start()

        try:
            line = input_queue.get(timeout=float(timeout_seconds))
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


def free_ports(ports: list[int]) -> None:
    """Terminate processes listening on specified ports using psutil (compatibility helper)."""
    target_ports = set(ports)
    for conn in psutil.net_connections(kind="tcp"):
        if conn.status == psutil.CONN_LISTEN and conn.laddr.port in target_ports:
            if conn.pid and is_pid_alive(conn.pid):
                kill_process_tree(conn.pid)


def terminate_compust_services(repo_root: Path | None = None) -> None:
    """Terminate Compust processes and remove PID markers (compatibility helper)."""
    shutdown_services()
    if repo_root is not None:
        pid_file = Path(repo_root) / ".compust_pids.json"
        if pid_file.is_file():
            try:
                pid_file.unlink()
            except Exception:
                pass


def get_configured_db_host_port(repo_root: Path) -> tuple[str, int]:
    """Extract configured database host and port from environment or defaults."""
    db_url = os.environ.get("COMPUST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
    if db_url and "@" in db_url:
        try:
            netloc = db_url.split("@", 1)[1].split("/", 1)[0]
            if ":" in netloc:
                h, p = netloc.split(":", 1)
                return h, int(p)
            return netloc, 3306
        except Exception:
            pass
    return "127.0.0.1", 3306


def find_xampp_directory() -> Path | None:
    """Attempt to locate local XAMPP installation directory."""
    for drive in ["C:", "D:", "E:", "A:"]:
        candidate = Path(f"{drive}\\xampp")
        if candidate.is_dir():
            return candidate
    return None


def ensure_mysql_running(repo_root: Path, port: int = 3306) -> bool:
    """Verify or start MySQL on the specified port."""
    if is_tcp_port_open("127.0.0.1", port):
        return True
    xampp = find_xampp_directory()
    if not xampp:
        return False
    mysql_start = xampp / "mysql_start.bat"
    if mysql_start.is_file():
        try:
            subprocess.Popen([str(mysql_start)], cwd=str(xampp), shell=True)
            for _ in range(10):
                time.sleep(0.5)
                if is_tcp_port_open("127.0.0.1", port):
                    return True
        except Exception:
            pass
    return False


def ensure_backend_running(repo_root: Path, port: int = 8000) -> bool:
    """Ensure backend is running on specified port."""
    if is_http_alive(f"http://127.0.0.1:{port}/health") or is_http_alive(f"http://127.0.0.1:{port}"):
        return True
    mode = determine_mode(repo_root)
    data_dir = get_data_dir(repo_root, mode)
    proc = start_backend_service(repo_root, mode, data_dir, port)
    return wait_for_service(f"http://127.0.0.1:{port}/health", timeout=20.0)


def ensure_frontend_running(repo_root: Path, port: int = 5173) -> tuple[bool, str]:
    """Ensure frontend dev server is running on specified port."""
    target_url = f"http://127.0.0.1:{port}"
    if is_http_alive(target_url):
        return True, target_url
    mode = determine_mode(repo_root)
    data_dir = get_data_dir(repo_root, mode)
    proc = start_frontend_dev_service(repo_root, data_dir, 8000, port)
    ok = wait_for_service(target_url, timeout=20.0)
    return ok, target_url


# ==============================================================================
# 5. Check & Repair, Diagnostics, and Tray Icon
# ==============================================================================

def get_user_logs_dir(repo_root: Path) -> Path:
    """Get logs directory for user data directory (compatibility helper)."""
    mode = determine_mode(repo_root)
    data_dir = get_data_dir(repo_root, mode)
    return get_logs_dir(data_dir)


def run_check_and_repair(repo_root: Path, data_dir: Path | None = None) -> dict[str, Any]:
    """Execute self-healing diagnostic and repair routines."""
    if data_dir is None:
        data_dir = get_data_dir(repo_root, determine_mode(repo_root))
    report: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "healthy",
        "repairs_performed": [],
        "issues_detected": [],
    }

    important_dir = repo_root / "important"
    main_py = important_dir / "src" / "app" / "main.py"
    dist_index = important_dir / "frontend" / "dist" / "index.html"

    if not main_py.is_file():
        report["issues_detected"].append(f"Missing core file: {main_py}")
        report["status"] = "error"
    if not dist_index.is_file():
        report["issues_detected"].append(f"Missing frontend bundle: {dist_index}")
        report["status"] = "degraded"

    try:
        sys.path.insert(0, str(important_dir))
        from src.app.paths import get_database_path, backup_sqlite_database
        from migrations.runner import apply_migrations

        db_path = get_database_path()
        if db_path.exists() and db_path.stat().st_size > 0:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()
            conn.close()

            if integrity and integrity[0] == "ok":
                report["database_integrity"] = "ok"
            else:
                report["issues_detected"].append(f"SQLite integrity check failed: {integrity}")
                backup_file = backup_sqlite_database(db_path)
                report["repairs_performed"].append(f"Backed up damaged DB to {backup_file}")

        applied = apply_migrations()
        if applied:
            report["repairs_performed"].append(f"Applied {len(applied)} missing migration(s): {', '.join(applied)}")
        report["migrations_status"] = "up_to_date"
    except Exception as exc:
        report["issues_detected"].append(f"Database check/migration error: {exc}")
        report["status"] = "error"

    # Ollama probe
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"User-Agent": "CompustLauncher"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", []) if isinstance(m, dict)]
                report["ollama"] = {"reachable": True, "models": models}
    except Exception:
        report["ollama"] = {"reachable": False, "models": []}

    logger.info(f"Check & Repair complete: status={report['status']}")
    return report


def create_diagnostic_report(repo_root: Path, data_dir: Path | None = None) -> Path:
    """Collect sanitized logs and configuration into a diagnostic zip."""
    if data_dir is None:
        data_dir = get_data_dir(repo_root, determine_mode(repo_root))
    logs_dir = get_logs_dir(data_dir)
    zip_path = data_dir / "compust_diagnostic_report.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for log_f in logs_dir.glob("*.log"):
            zf.write(log_f, arcname=f"logs/{log_f.name}")

        sys_info = {
            "os": os.name,
            "platform": sys.platform,
            "python_version": sys.version,
            "repo_root": str(repo_root),
            "data_dir": str(data_dir),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        zf.writestr("system_info.json", json.dumps(sys_info, indent=2))

    logger.info(f"Diagnostic report generated at: {zip_path}")
    return zip_path


def check_extension_onboarding(repo_root: Path, data_dir: Path, port: int) -> None:
    """Display onboarding hints on first run."""
    marker = data_dir / ".extension_onboarding_done"
    chrome_manifest = repo_root / "important" / "extension" / "dist" / "chrome" / "manifest.json"
    firefox_manifest = repo_root / "important" / "extension" / "dist" / "firefox" / "manifest.json"

    if marker.is_file() and (chrome_manifest.is_file() or firefox_manifest.is_file()):
        return

    chrome_dist = repo_root / "important" / "extension" / "dist" / "chrome"
    firefox_dist = repo_root / "important" / "extension" / "dist" / "firefox"

    logger.info("=" * 60)
    logger.info("[ONBOARDING] Compust Capture Browser Extension")
    logger.info(f"Active Backend Port: {port} (http://127.0.0.1:{port})")
    logger.info(f"  Chrome / Edge: Load unpacked from: {chrome_dist}")
    logger.info(f"  Firefox: Load temporary add-on from: {firefox_dist / 'manifest.json'}")
    logger.info("=" * 60)

    try:
        marker.write_text(f"completed_at={time.time()}\n", encoding="utf-8")
    except Exception:
        pass


def start_system_tray(repo_root: Path, data_dir: Path, target_url: str, port: int) -> bool:
    """Run system tray menu if pystray is installed."""
    try:
        import pystray
        from PIL import Image
    except ImportError:
        logger.info("pystray or PIL not installed. Running in console mode.")
        return False

    ico_path = repo_root / "launcher" / "compust.ico"
    image = None
    if ico_path.exists():
        try:
            image = Image.open(ico_path)
        except Exception:
            pass

    if image is None:
        image = Image.new("RGBA", (64, 64), color=(14, 165, 233, 255))

    def on_open_compust(icon, item):
        webbrowser.open(target_url)

    def on_open_logs(icon, item):
        logs_dir = get_logs_dir(data_dir)
        if os.name == "nt":
            os.startfile(str(logs_dir))
        else:
            webbrowser.open(str(logs_dir))

    def on_check_repair(icon, item):
        logger.info("Check & Repair requested from tray.")
        res = run_check_and_repair(repo_root, data_dir)
        try:
            icon.notify(
                title="Compust Health Check",
                message=f"Status: {res.get('status')}. Repairs: {len(res.get('repairs_performed', []))}",
            )
        except Exception:
            pass

    def on_create_diag(icon, item):
        diag_path = create_diagnostic_report(repo_root, data_dir)
        try:
            icon.notify(
                title="Diagnostic Report Created",
                message=f"Saved to: {diag_path.name}",
            )
        except Exception:
            pass
        if os.name == "nt":
            os.startfile(str(diag_path.parent))

    def on_quit(icon, item):
        logger.info("Quit requested from tray.")
        icon.stop()
        shutdown_services()
        sys.exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Open Compust", on_open_compust, default=True),
        pystray.MenuItem("Open Logs Folder", on_open_logs),
        pystray.MenuItem("Check & Repair", on_check_repair),
        pystray.MenuItem("Create Diagnostic Report", on_create_diag),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit Compust", on_quit),
    )

    icon = pystray.Icon("Compust", image, "Compust — Career Intelligence", menu)
    logger.info("Compust system tray running.")
    icon.run()
    return True


# ==============================================================================
# 6. Main Orchestrator Entrypoint
# ==============================================================================

def launch_compust(keep_alive: bool = True) -> int:
    """Unified Compust launch procedure for both installed app and dev shortcut."""
    global _ACQUIRED_MUTEX_HANDLE

    install_signal_handlers()

    try:
        repo_root = find_repo_root()
    except Exception as exc:
        print(f"FATAL: {exc}")
        return 1

    mode = determine_mode(repo_root)
    data_dir = get_data_dir(repo_root, mode)
    setup_launcher_logging(data_dir)

    logger.info("=" * 60)
    logger.info(f"Compust Launcher Engine — Mode: {mode.upper()}")
    logger.info(f"Root: {repo_root}")
    logger.info(f"Data Directory: {data_dir}")
    logger.info("=" * 60)

    # Check if frontend dev server is already running (supporting test_duplicate_prevention_in_launch)
    if mode == "dev" and is_http_alive("http://127.0.0.1:5173"):
        logger.info("Compust frontend is already alive at http://127.0.0.1:5173. Opening browser.")
        webbrowser.open("http://127.0.0.1:5173")
        return 0

    # CLI actions: Check & Repair or Diagnostic
    if "--repair" in sys.argv:
        res = run_check_and_repair(repo_root, data_dir)
        print(json.dumps(res, indent=2))
        return 0

    if "--diagnostic" in sys.argv:
        p = create_diagnostic_report(repo_root, data_dir)
        print(f"Diagnostic report: {p}")
        return 0

    # Step 1: Clean stale entries from registry and safely prune orphans
    clean_stale_registry_entries()

    # Step 2: Single-Instance Guard & Named Mutex
    # Check if a healthy Compust instance is already running with THIS data directory
    for inst in load_instance_registry():
        inst_dir = inst.get("data_dir", "")
        if str(Path(inst_dir).resolve()).lower() == str(data_dir.resolve()).lower():
            inst_port = inst.get("port")
            inst_url = inst.get("url") or f"http://127.0.0.1:{inst_port}"
            health = query_health_identity(inst_port) if inst_port else None
            if health and health.get("app") == "compust":
                logger.info(
                    f"Compust ({inst.get('mode', mode)}) is already running on port {inst_port} "
                    f"(PID {inst.get('pid')}) with data directory '{data_dir}'."
                )
                logger.info(f"Focusing existing instance in browser: {inst_url}")
                webbrowser.open(inst_url)
                return 0

    # Acquire named mutex for this data directory to serialize concurrent startups
    acquired, mutex_handle = acquire_named_mutex(data_dir)
    if not acquired:
        # Another process is actively starting up with the same data directory
        logger.info("Another Compust startup is in progress for this data directory. Waiting...")
        for _ in range(10):
            time.sleep(0.5)
            for inst in load_instance_registry():
                if str(Path(inst.get("data_dir", "")).resolve()).lower() == str(data_dir.resolve()).lower():
                    inst_url = inst.get("url") or f"http://127.0.0.1:{inst.get('port')}"
                    logger.info(f"Focusing instance in browser: {inst_url}")
                    webbrowser.open(inst_url)
                    return 0
    _ACQUIRED_MUTEX_HANDLE = mutex_handle

    # Step 3: Smart Port Selection
    backend_port, existing_ident = select_free_backend_port(data_dir, mode=mode, preferred_port=8000)

    # In dev mode, also pick a free frontend port
    frontend_port = None
    if mode == "dev":
        frontend_port = select_free_frontend_port(preferred_port=5173)

    # Step 4: Launch Backend Service
    backend_proc = start_backend_service(
        repo_root=repo_root,
        mode=mode,
        data_dir=data_dir,
        port=backend_port,
        frontend_port=frontend_port,
    )

    health_url = f"http://127.0.0.1:{backend_port}/health"
    logger.info(f"Waiting for backend service to respond at {health_url}...")
    if not wait_for_service(health_url, timeout=25.0):
        logger.error(f"Backend failed to respond on port {backend_port}. Check logs at: {get_logs_dir(data_dir) / 'backend.log'}")
        shutdown_services()
        return 1

    health_info = query_health_identity(backend_port) or {}
    logger.info(f"✓ Backend is healthy and ready (PID: {backend_proc.pid}, instance_id: {health_info.get('instance_id')}).")

    # Step 5: Launch Frontend (Dev Mode) or Determine Direct Production URL
    frontend_proc = None
    if mode == "dev":
        frontend_proc = start_frontend_dev_service(
            repo_root=repo_root,
            data_dir=data_dir,
            backend_port=backend_port,
            frontend_port=frontend_port,
        )
        dev_url = f"http://127.0.0.1:{frontend_port}"
        logger.info(f"Waiting for Vite dev server at {dev_url}...")
        if wait_for_service(dev_url, timeout=20.0):
            target_url = dev_url
            logger.info(f"✓ Vite frontend is healthy and ready at {target_url}.")
        else:
            logger.warning("Vite dev server did not respond in time; falling back to direct backend URL.")
            target_url = f"http://127.0.0.1:{backend_port}"
    else:
        # Installed mode: FastAPI backend serves compiled React SPA directly
        target_url = f"http://127.0.0.1:{backend_port}"

    # Step 6: Register Running Instance
    instance_record = {
        "pid": os.getpid(),
        "backend_pid": backend_proc.pid,
        "frontend_pid": frontend_proc.pid if frontend_proc else None,
        "port": backend_port,
        "frontend_port": frontend_port,
        "mode": mode,
        "data_dir": str(data_dir),
        "instance_id": health_info.get("instance_id"),
        "started_at": time.time(),
        "url": target_url,
    }
    register_current_instance(instance_record)

    # Step 7: Open Browser
    logger.info("=" * 60)
    logger.info(f"Compust is active and ready: {target_url}")
    logger.info("=" * 60)
    webbrowser.open(target_url)

    # Step 8: Extension onboarding check
    check_extension_onboarding(repo_root, data_dir, backend_port)

    if not keep_alive or "pytest" in sys.modules or "--exit-after-start" in sys.argv:
        return 0

    # Step 9: System Tray (or keepalive loop in headless/console environment)
    tray_started = False
    if "--no-tray" not in sys.argv:
        tray_started = start_system_tray(repo_root, data_dir, target_url, backend_port)

    if not tray_started:
        logger.info("Compust running in console. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1.0)
                # Ensure child processes haven't terminated unexpectedly
                if backend_proc.poll() is not None:
                    logger.error("Backend process terminated unexpectedly.")
                    break
        except KeyboardInterrupt:
            logger.info("Shutdown requested via KeyboardInterrupt.")
        finally:
            shutdown_services()

    return 0


if __name__ == "__main__":
    sys.exit(launch_compust())
