@echo off
chcp 65001 >nul
title AutoInsta - Windows Dependency Installer

echo ====================================================================
echo             AUTOINSTA - INSTALLATION DES DÉPENDANCES PC
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
pause
exit /b 1

:found_python
set PROJECT_ROOT=%~dp0..\..

echo [*] Mise à niveau de pip...
%PYTHON_CMD% -m pip install --upgrade pip

echo [*] Installation des dépendances depuis requirements.txt...
%PYTHON_CMD% -m pip install -r "%PROJECT_ROOT%\requirements.txt"

if not exist "%PROJECT_ROOT%\.env" (
    if exist "%PROJECT_ROOT%\.env.example" (
        echo [*] Initialisation du fichier de configuration .env...
        copy "%PROJECT_ROOT%\.env.example" "%PROJECT_ROOT%\.env" >nul
    )
)

echo.
echo ====================================================================
echo  [✓] INSTALLATION TERMINÉE AVEC SUCCÈS !
echo  Pour démarrer AutoInsta, lancez :
echo    scripts\windows\start.bat
echo ====================================================================
pause
