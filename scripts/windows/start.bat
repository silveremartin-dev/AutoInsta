@echo off
chcp 65001 >nul
title AutoInsta - Windows Launcher

echo ====================================================================
echo                   AUTOINSTA - LANCEUR WINDOWS
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

echo [!] ERREUR : Python est introuvable sur votre système !
echo     Veuillez installer Python 3.10+ depuis https://www.python.org/
echo     et cocher la case "Add Python to PATH".
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
    echo [!] Le programme s'est arrêté avec une erreur.
    pause
)
