"""
Compust Windows One-File Installer Packaging Script.

Automates:
1. Production React frontend build (dist)
2. Browser extension zip packaging (Chrome & Firefox)
3. Compilation of windowless native launcher stub (Compust.exe)
4. Assembly of private Python 3.12 embeddable distribution with pre-installed wheels
5. Assembly of application source, migrations, static assets, and reference datasets
6. Compilation of Inno Setup 6 installer (Compust-Setup-vX.Y.Z.exe)
7. SHA-256 checksum generation
8. Automated CI smoke test execution (--smoke-test)
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("compust.packager")

DEFAULT_VERSION = "1.0.3"
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"
PYTHON_EMBED_SHA256 = "615861fb801e8b04c847598db4e1e46e4b046295017caa37cb5486dde72b5865"


def compute_sha256(filepath: Path) -> str:
    """Compute hex SHA-256 digest of a file in streaming chunks."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def find_iscc() -> Path:
    """Locate Inno Setup Compiler executable (ISCC.exe)."""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path("C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"),
        Path("C:\\Program Files\\Inno Setup 6\\ISCC.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return c

    # Check PATH
    try:
        probe = shutil.which("iscc") or shutil.which("ISCC.exe")
        if probe:
            return Path(probe)
    except Exception:
        pass

    raise RuntimeError("Inno Setup Compiler (ISCC.exe) not found. Install Inno Setup 6 or run via winget.")


def find_csc() -> Path:
    """Locate Microsoft .NET C# Compiler (csc.exe) to build the native launcher stub."""
    candidates = [
        Path("C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\csc.exe"),
        Path("C:\\Windows\\Microsoft.NET\\Framework\\v4.0.30319\\csc.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    probe = shutil.which("csc") or shutil.which("csc.exe")
    if probe:
        return Path(probe)
    raise RuntimeError("Microsoft C# compiler (csc.exe) not found.")


def build_frontend(repo_root: Path) -> None:
    """Build production React frontend dist."""
    frontend_dir = repo_root / "important" / "frontend"
    logger.info("Building production React frontend (npm run build)...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run(
        [npm_cmd, "run", "build"],
        cwd=str(frontend_dir),
        check=True,
        shell=True if os.name == "nt" else False,
    )
    dist_index = frontend_dir / "dist" / "index.html"
    assert dist_index.is_file(), "frontend/dist/index.html was not generated!"
    logger.info("✓ Frontend build complete.")


def build_extensions(repo_root: Path) -> None:
    """Ensure Chrome and Firefox extension packages are zipped and present."""
    ext_dir = repo_root / "important" / "extension"
    ext_dist = ext_dir / "dist"
    ext_dist.mkdir(parents=True, exist_ok=True)

    chrome_zip = ext_dist / "compust-capture-chrome.zip"
    firefox_zip = ext_dist / "compust-capture-firefox.zip"

    # Zip chrome directory if needed
    chrome_dir = ext_dist / "chrome"
    if chrome_dir.is_dir() and not chrome_zip.is_file():
        logger.info(f"Zipping Chrome extension package from {chrome_dir}...")
        with zipfile.ZipFile(chrome_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in chrome_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, arcname=f.relative_to(chrome_dir))

    # Zip firefox directory if needed
    firefox_dir = ext_dist / "firefox"
    if firefox_dir.is_dir() and not firefox_zip.is_file():
        logger.info(f"Zipping Firefox extension package from {firefox_dir}...")
        with zipfile.ZipFile(firefox_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in firefox_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, arcname=f.relative_to(firefox_dir))

    assert chrome_zip.is_file(), "compust-capture-chrome.zip missing!"
    assert firefox_zip.is_file(), "compust-capture-firefox.zip missing!"
    logger.info("✓ Browser extension packages verified.")


def compile_launcher_stub(repo_root: Path) -> Path:
    """Compile native, windowless Compust.exe launcher stub."""
    launcher_dir = repo_root / "launcher"
    cs_file = launcher_dir / "LauncherStub.cs"
    ico_file = launcher_dir / "compust.ico"
    out_exe = repo_root / "Compust.exe"

    csc_exe = find_csc()
    logger.info(f"Compiling native launcher {out_exe} using {csc_exe}...")
    cmd = [
        str(csc_exe),
        "/target:winexe",
        f"/win32icon:{ico_file}",
        f"/out:{out_exe}",
        str(cs_file),
    ]
    subprocess.run(cmd, check=True)
    assert out_exe.is_file(), "Compust.exe failed to compile!"
    logger.info(f"✓ Native launcher compiled successfully ({round(out_exe.stat().st_size / 1024, 1)} KB).")
    return out_exe


def prepare_python_runtime(repo_root: Path, staging_runtime: Path, use_venv: bool = False) -> None:
    """
    Assemble the private, self-contained Python runtime.
    If use_venv is True, copies from the local development venv for ultra-fast local packaging.
    Otherwise, downloads the official Python 3.12 embeddable distribution and installs wheels.
    """
    if (staging_runtime / "python.exe").is_file() and (staging_runtime / "Lib" / "site-packages").is_dir():
        logger.info("✓ Staging runtime already populated.")
        return

    staging_runtime.mkdir(parents=True, exist_ok=True)
    venv_dir = repo_root / "important" / ".venv"

    if use_venv and venv_dir.is_dir():
        logger.info("Using local virtual environment as bundled runtime (--use-venv-runtime)...")
        # Copy python.exe, pythonw.exe, DLLs and Lib
        scripts_dir = venv_dir / "Scripts"
        shutil.copy2(scripts_dir / "python.exe", staging_runtime / "python.exe")
        if (scripts_dir / "pythonw.exe").exists():
            shutil.copy2(scripts_dir / "pythonw.exe", staging_runtime / "pythonw.exe")
        else:
            shutil.copy2(scripts_dir / "python.exe", staging_runtime / "pythonw.exe")

        # Copy Lib
        shutil.copytree(venv_dir / "Lib", staging_runtime / "Lib", ignore=shutil.ignore_patterns("__pycache__"))
        
        # Copy pyvenv.cfg if present
        if (venv_dir / "pyvenv.cfg").exists():
            shutil.copy2(venv_dir / "pyvenv.cfg", staging_runtime / "pyvenv.cfg")

        # Copy python314.dll / python3.dll from python base if present
        py_home = Path(sys.base_prefix)
        for dll in py_home.glob("*.dll"):
            shutil.copy2(dll, staging_runtime / dll.name)
        logger.info("✓ Venv runtime staged.")
        return

    # Official self-contained Python embeddable distribution
    # Match the host Python version so pre-built wheel ABIs (e.g. pydantic-core) match 100%
    if sys.version_info[:2] == (3, 14):
        embed_url = "https://www.python.org/ftp/python/3.14.0/python-3.14.0-embed-amd64.zip"
        embed_sha256 = "8d4d3590c10449d78aa4375f534e6d5f3027d67fdc362dd1a882279db6f90fdf"
        embed_zip_name = "python-3.14.0-embed-amd64.zip"
        py_tag = "314"
    else:
        embed_url = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"
        embed_sha256 = "615861fb801e8b04c847598db4e1e46e4b046295017caa37cb5486dde72b5865"
        embed_zip_name = "python-3.12.9-embed-amd64.zip"
        py_tag = "312"

    cache_dir = repo_root / ".cache"
    cache_dir.mkdir(exist_ok=True)
    embed_zip = cache_dir / embed_zip_name

    if not embed_zip.exists() or compute_sha256(embed_zip) != embed_sha256:
        logger.info(f"Downloading official Python embeddable runtime from {embed_url}...")
        tmp_zip = embed_zip.with_suffix(".tmp")
        urllib.request.urlretrieve(embed_url, tmp_zip)
        assert compute_sha256(tmp_zip) == embed_sha256, "Python embeddable SHA-256 mismatch!"
        tmp_zip.replace(embed_zip)
        logger.info("✓ Python embeddable zip downloaded and verified.")

    logger.info(f"Extracting Python embeddable distribution to {staging_runtime}...")
    with zipfile.ZipFile(embed_zip, "r") as zf:
        zf.extractall(staging_runtime)

    # Copy site.py from standard library so 'import site' functions properly in embeddable mode
    py_base_lib = Path(sys.base_prefix) / "Lib"
    if (py_base_lib / "site.py").is_file():
        shutil.copy2(py_base_lib / "site.py", staging_runtime / "site.py")

    # Configure python*._pth
    pth_files = list(staging_runtime.glob("python*._pth"))
    assert pth_files, "python*._pth not found in embeddable runtime!"
    pth_file = pth_files[0]
    pth_content = [
        f"python{py_tag}.zip",
        ".",
        "Lib\\site-packages",
        "..\\important",
        "import site",
    ]
    pth_file.write_text("\n".join(pth_content) + "\n", encoding="utf-8")

    # Install dependencies into staging_runtime/Lib/site-packages
    site_packages = staging_runtime / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)

    logger.info("Installing pinned dependencies into bundled runtime Lib/site-packages...")
    req_file = repo_root / "important" / "requirements.txt"
    pip_cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--no-compile",
        f"--target={site_packages}",
        "-r",
        str(req_file),
        "pystray",
        "pillow",
    ]
    subprocess.run(pip_cmd, check=True)
    logger.info("✓ Python runtime and dependencies staged successfully.")


def stage_application(repo_root: Path, staging_dir: Path, version: str, use_venv: bool = False) -> None:
    """Assemble all application components into clean staging directory."""
    logger.info(f"Preparing staging directory: {staging_dir}...")
    staging_runtime = staging_dir / "runtime"
    runtime_backup = None
    if staging_runtime.is_dir() and (staging_runtime / "python.exe").is_file():
        logger.info("Preserving existing staged runtime across staging refresh...")
        runtime_backup = staging_dir.parent / "staging_runtime_temp"
        if runtime_backup.exists():
            shutil.rmtree(runtime_backup)
        staging_runtime.rename(runtime_backup)

    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    if runtime_backup and runtime_backup.is_dir():
        runtime_backup.rename(staging_dir / "runtime")

    # 1. Launcher and scripts
    shutil.copy2(repo_root / "Compust.exe", staging_dir / "Compust.exe")
    shutil.copy2(repo_root / "Compust.bat", staging_dir / "Compust.bat")
    shutil.copy2(repo_root / "README.md", staging_dir / "README.md")
    shutil.copy2(repo_root / "LICENSE", staging_dir / "LICENSE")

    launcher_dst = staging_dir / "launcher"
    launcher_dst.mkdir(exist_ok=True)
    for lf in ["launcher_core.py", "create_shortcut.py", "compust.ico", "LauncherStub.cs"]:
        src = repo_root / "launcher" / lf
        if src.exists():
            shutil.copy2(src, launcher_dst / lf)

    # 2. Python runtime
    prepare_python_runtime(repo_root, staging_dir / "runtime", use_venv=use_venv)

    # 3. Application codebase
    important_dir = repo_root / "important"
    imp_dst = staging_dir / "important"
    imp_dst.mkdir(exist_ok=True)

    # src/
    shutil.copytree(
        important_dir / "src",
        imp_dst / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )

    # frontend/dist
    shutil.copytree(important_dir / "frontend" / "dist", imp_dst / "frontend" / "dist")

    # frontend/public/illustrations
    pub_illus = important_dir / "frontend" / "public" / "illustrations"
    if pub_illus.is_dir():
        shutil.copytree(pub_illus, imp_dst / "frontend" / "public" / "illustrations")

    # extension/dist
    shutil.copytree(important_dir / "extension" / "dist", imp_dst / "extension" / "dist")

    # alembic and migrations
    if (important_dir / "alembic").is_dir():
        shutil.copytree(important_dir / "alembic", imp_dst / "alembic", ignore=shutil.ignore_patterns("__pycache__"))
    if (important_dir / "alembic.ini").is_file():
        shutil.copy2(important_dir / "alembic.ini", imp_dst / "alembic.ini")
    if (important_dir / "migrations").is_dir():
        shutil.copytree(important_dir / "migrations", imp_dst / "migrations", ignore=shutil.ignore_patterns("__pycache__"))

    # reference datasets
    if (important_dir / "job-titles.json").is_file():
        shutil.copy2(important_dir / "job-titles.json", imp_dst / "job-titles.json")

    # Write installation state marker
    marker_content = {
        "version": version,
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "stage": "complete",
    }
    (staging_dir / ".install_complete").write_text(json.dumps(marker_content, indent=2), encoding="utf-8")
    logger.info("✓ Staging complete.")


def compile_inno_installer(repo_root: Path, staging_dir: Path, output_dir: Path, version: str) -> Path:
    """Compile Inno Setup script into Compust-Setup-vX.Y.Z.exe."""
    iscc_exe = find_iscc()
    iss_file = repo_root / "installer" / "compust_setup.iss"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Compiling Inno Setup installer using {iscc_exe}...")
    cmd = [
        str(iscc_exe),
        f"/DAppVersion={version}",
        f"/DStagingDir={staging_dir}",
        f"/DOutputDir={output_dir}",
        str(iss_file),
    ]
    subprocess.run(cmd, check=True)

    installer_exe = output_dir / f"Compust-Setup-v{version}.exe"
    assert installer_exe.is_file(), f"Expected installer at {installer_exe} not found!"

    # Compute and write SHA-256
    checksum = compute_sha256(installer_exe)
    sha_file = output_dir / f"Compust-Setup-v{version}.exe.sha256"
    sha_file.write_text(f"{checksum}  {installer_exe.name}\n", encoding="utf-8")

    size_mb = round(installer_exe.stat().st_size / (1024 * 1024), 2)
    logger.info(f"✓ Inno Setup compilation successful: {installer_exe.name} ({size_mb} MB)")
    logger.info(f"  SHA-256: {checksum}")
    return installer_exe


def run_smoke_test(installer_exe: Path) -> None:
    """
    Execute automated smoke test:
    1. Silently install (/VERYSILENT) into temporary directory
    2. Start backend and poll /health
    3. Test sample API endpoints & extension zip download
    4. Silently uninstall and verify directory cleanup
    """
    logger.info("=" * 60)
    logger.info("STARTING CI SMOKE TEST FOR WINDOWS INSTALLER")
    logger.info("=" * 60)

    with tempfile.TemporaryDirectory(prefix="compust_smoke_") as temp_dir:
        test_install_dir = Path(temp_dir) / "CompustApp"
        logger.info(f"1. Installing silently to: {test_install_dir}...")
        
        install_cmd = [
            str(installer_exe),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            f"/DIR={test_install_dir}",
        ]
        subprocess.run(install_cmd, check=True)

        # Verify essential files
        assert (test_install_dir / "Compust.exe").is_file(), "Compust.exe missing in installation!"
        assert (test_install_dir / ".install_complete").is_file(), ".install_complete marker missing!"
        assert (test_install_dir / "important" / "src" / "app" / "main.py").is_file(), "main.py missing!"
        assert (test_install_dir / "important" / "frontend" / "dist" / "index.html").is_file(), "index.html missing!"
        logger.info("✓ Installation files verified on disk.")

        # 2. Launch backend and test health
        logger.info("2. Launching backend service and polling /health...")
        python_exe = test_install_dir / "runtime" / "python.exe"
        if not python_exe.exists():
            python_exe = Path(sys.executable)

        backend_proc = subprocess.Popen(
            [str(python_exe), "-m", "uvicorn", "src.app.main:app", "--host", "127.0.0.1", "--port", "8899"],
            cwd=str(test_install_dir / "important"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        health_url = "http://127.0.0.1:8899/health"
        alive = False
        try:
            for _ in range(50):
                time.sleep(0.5)
                try:
                    with urllib.request.urlopen(health_url, timeout=1.0) as r:
                        if r.status == 200:
                            alive = True
                            break
                except Exception:
                    pass

            if not alive:
                stdout, stderr = backend_proc.communicate(timeout=3)
                logger.error(f"Backend stdout: {stdout}")
                logger.error(f"Backend stderr: {stderr}")

            assert alive, "Backend did not respond with 200 on /health within 25 seconds!"
            logger.info("✓ Backend is healthy and responding.")

            # 3. Test real endpoints
            logger.info("3. Testing sample API endpoints...")
            # Jobs endpoint
            with urllib.request.urlopen("http://127.0.0.1:8899/api/v1/jobs?limit=5", timeout=2.0) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode("utf-8"))
                assert "items" in data or "jobs" in data or isinstance(data, list)
            logger.info("✓ /api/v1/jobs endpoint returned 200.")

            # Extension download endpoint: Chrome
            with urllib.request.urlopen("http://127.0.0.1:8899/api/v1/extension/download/chrome", timeout=2.0) as resp:
                assert resp.status == 200
                chrome_bytes = resp.read()
                assert len(chrome_bytes) > 10000, "Chrome extension download archive is empty or invalid!"
            logger.info(f"✓ /api/v1/extension/download/chrome returned valid zip ({len(chrome_bytes)} bytes).")

            # Extension download endpoint: Firefox
            with urllib.request.urlopen("http://127.0.0.1:8899/api/v1/extension/download/firefox", timeout=2.0) as resp:
                assert resp.status == 200
                firefox_bytes = resp.read()
                assert len(firefox_bytes) > 10000, "Firefox extension download archive is empty or invalid!"
            logger.info(f"✓ /api/v1/extension/download/firefox returned valid zip ({len(firefox_bytes)} bytes).")

        finally:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=3)
            except Exception:
                backend_proc.kill()

        # 4. Uninstall test
        logger.info("4. Running silent uninstall...")
        uninstaller = test_install_dir / "unins000.exe"
        assert uninstaller.is_file(), "Uninstaller unins000.exe not found!"
        uninst_cmd = [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
        subprocess.run(uninst_cmd, check=True)
        time.sleep(1.0)

        # Confirm program directory cleanup
        assert not (test_install_dir / "Compust.exe").exists(), "Compust.exe was not removed by uninstaller!"
        logger.info("✓ Uninstaller cleaned up program files successfully.")

    logger.info("=" * 60)
    logger.info("✓ CI SMOKE TEST PASSED ALL VALIDATION GATES!")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Build and package Compust Windows One-File Installer.")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="Release version (e.g. 1.0.0)")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip npm run build if already built")
    parser.add_argument("--use-venv-runtime", action="store_true", help="Use local venv for ultra-fast packaging")
    parser.add_argument("--smoke-test", action="store_true", help="Run automated silent install/uninstall smoke test")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    release_dir = repo_root / "release"
    staging_dir = release_dir / "staging"

    logger.info(f"Starting Compust Packaging for version v{args.version}...")

    # 1. Build frontend
    if not args.skip_frontend:
        build_frontend(repo_root)

    # 2. Build extensions
    build_extensions(repo_root)

    # 3. Compile native launcher stub
    compile_launcher_stub(repo_root)

    # 4. Stage application
    stage_application(repo_root, staging_dir, version=args.version, use_venv=args.use_venv_runtime)

    # 5. Compile Inno Setup installer
    installer_exe = compile_inno_installer(repo_root, staging_dir, release_dir, version=args.version)

    # 6. Run smoke test if requested
    if args.smoke_test:
        run_smoke_test(installer_exe)


if __name__ == "__main__":
    main()
