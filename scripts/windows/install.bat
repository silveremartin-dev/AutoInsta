@echo off
chcp 65001 >nul
title AutoInsta - Windows Dependency Installer

echo ====================================================================
echo             AUTOINSTA - PC DEPENDENCY INSTALLER
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
pause
exit /b 1

:found_python
set PROJECT_ROOT=%~dp0..\..

echo [*] Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip

echo [*] Installing dependencies from requirements.txt...
%PYTHON_CMD% -m pip install -r "%PROJECT_ROOT%\requirements.txt"

if not exist "%PROJECT_ROOT%\.env" (
    if exist "%PROJECT_ROOT%\.env.example" (
        echo [*] Initializing .env configuration file...
        copy "%PROJECT_ROOT%\.env.example" "%PROJECT_ROOT%\.env" >nul
    )
)

echo.
echo ====================================================================
echo  [✓] INSTALLATION COMPLETED SUCCESSFULLY!
echo  To start AutoInsta, run:
echo    scripts\windows\start.bat
echo ====================================================================
pause
