@echo off
rem ==============================================================================
rem Compust - One-Click Windows Launcher
rem ==============================================================================
setlocal
cd /d "%~dp0"

set PYTHON_EXE=important\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

"%PYTHON_EXE%" launcher\launcher_core.py
exit /b %ERRORLEVEL%
