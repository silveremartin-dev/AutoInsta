@echo off
chcp 65001 >nul
title AutoInsta - Lanceur Principal

echo ====================================================================
echo                   AUTOINSTA - LANCEUR WINDOWS
echo ====================================================================

:: Detection of Python launcher or executable
set PYTHON_CMD=
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=python
    ) else (
        echo [!] ERREUR : Python est introuvable sur votre système !
        echo     Veuillez installer Python 3.10+ depuis https://www.python.org/
        echo     et cocher la case "Add Python to PATH".
        pause
        exit /b 1
    )
)

:: If arguments were passed to start.bat, forward them to start.py
if not "%~1"=="" (
    "%PYTHON_CMD%" "%~dp0start.py" %*
    goto :end
)

:: Otherwise run interactive launcher
"%PYTHON_CMD%" "%~dp0start.py"

:end
