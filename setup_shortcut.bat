@echo off
rem ==============================================================================
rem Compust - One-Time Windows Desktop Shortcut Setup
rem ==============================================================================
setlocal
cd /d "%~dp0"

set PYTHON_EXE=important\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

"%PYTHON_EXE%" launcher\create_shortcut.py
if %ERRORLEVEL% equ 0 (
    echo.
    echo ==============================================================================
    echo Compust Desktop shortcut created successfully!
    echo Double-click the "Compust" icon on your Desktop to launch the platform.
    echo ==============================================================================
) else (
    echo.
    echo [ERROR] Failed to create desktop shortcut.
)
pause
