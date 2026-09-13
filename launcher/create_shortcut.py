"""Create Windows Desktop shortcut for Compust with official icon."""

import os
import subprocess
from pathlib import Path
from launcher_core import find_repo_root


def get_desktop_folder() -> Path:
    """Retrieve localized Windows Desktop folder path dynamically via PowerShell."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True,
            text=True,
            check=True,
        )
        desktop_str = res.stdout.strip()
        if desktop_str and Path(desktop_str).is_dir():
            return Path(desktop_str)
    except Exception:
        pass

    # Fallback options
    user_home = Path.home()
    for candidate in [
        user_home / "OneDrive" / "Bureau",
        user_home / "OneDrive" / "Desktop",
        user_home / "Bureau",
        user_home / "Desktop",
    ]:
        if candidate.is_dir():
            return candidate

    return user_home / "Desktop"


def create_desktop_shortcut() -> Path:
    """Create Windows Desktop shortcut for Compust pointing to Compust.bat."""
    repo_root = find_repo_root()
    bat_path = repo_root / "Compust.bat"
    ico_path = repo_root / "launcher" / "compust.ico"
    desktop_dir = get_desktop_folder()
    desktop_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path = desktop_dir / "Compust.lnk"
    repo_shortcut_path = repo_root / "Compust.lnk"

    # Ensure icon exists
    if not ico_path.exists():
        from generate_icon import generate_ico
        png_path = repo_root / "important" / "frontend" / "public" / "logo-transparent.png"
        generate_ico(png_path, ico_path)

    # Escape paths for safe PowerShell interpolation
    s_path = str(shortcut_path).replace("'", "''")
    b_path = str(bat_path).replace("'", "''")
    r_path = str(repo_root).replace("'", "''")
    i_path = str(ico_path).replace("'", "''")
    rs_path = str(repo_shortcut_path).replace("'", "''")

    # Use PowerShell to invoke WScript.Shell and create shortcut at both Desktop and repo root
    powershell_cmd = f"""
    $WshShell = New-Object -comObject WScript.Shell
    
    # 1. Desktop Shortcut
    $Shortcut = $WshShell.CreateShortcut('{s_path}')
    $Shortcut.TargetPath = '{b_path}'
    $Shortcut.WorkingDirectory = '{r_path}'
    $Shortcut.IconLocation = '{i_path},0'
    $Shortcut.Description = 'Compust - Local-First Career & Internship Intelligence Platform'
    $Shortcut.Save()

    # 2. Repo Root Shortcut
    $RepoShortcut = $WshShell.CreateShortcut('{rs_path}')
    $RepoShortcut.TargetPath = '{b_path}'
    $RepoShortcut.WorkingDirectory = '{r_path}'
    $RepoShortcut.IconLocation = '{i_path},0'
    $RepoShortcut.Description = 'Compust - Local-First Career & Internship Intelligence Platform'
    $RepoShortcut.Save()
    """

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", powershell_cmd],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Desktop shortcut created successfully at: {shortcut_path}")
        print(f"Repository shortcut created at: {repo_shortcut_path}")
    except subprocess.CalledProcessError as exc:
        print(f"Error creating shortcut: {exc.stderr}")
        raise

    return shortcut_path


if __name__ == "__main__":
    create_desktop_shortcut()
