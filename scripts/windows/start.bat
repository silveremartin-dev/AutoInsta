@echo off
chcp 65001 >nul
title AutoInsta - Windows Launcher

echo ====================================================================
echo                   AUTOINSTA - WINDOWS LAUNCHER
echo ====================================================================

set PYTHON_CMD=
py -3.14 -c "import sys" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py -3.14
    goto :found_python
)
py -3 -c "import sys" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py -3
    goto :found_python
)
py -c "import sys" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py
    goto :found_python
)
python -c "import sys" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=python
    goto :found_python
)

echo [!] ERROR: Python is not found on your system!
echo     Please install Python 3.10+ from https://www.python.org/
echo     and ensure "Add Python to PATH" is checked during setup.
pause
exit /b 1

:found_python
set SCRIPT_DIR=%~dp0
set LAUNCHER=%SCRIPT_DIR%..\server_launcher.py

if not "%~1"=="" (
    %PYTHON_CMD% "%LAUNCHER%" %*
    goto :done
)

%PYTHON_CMD% "%LAUNCHER%"

:done
if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Program terminated with an error.
    pause
)
