@echo off
chcp 65001 >nul
title AutoInsta - Installation des dépendances

echo ====================================================================
echo             AUTOINSTA - INSTALLATION DES DÉPENDANCES PC
echo ====================================================================

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
        pause
        exit /b 1
    )
)

echo [*] Mise à niveau de pip...
"%PYTHON_CMD%" -m pip install --upgrade pip

echo [*] Installation des paquets depuis requirements.txt...
"%PYTHON_CMD%" -m pip install -r "%~dp0requirements.txt"

if not exist "%~dp0.env" (
    if exist "%~dp0.env.example" (
        echo [*] Initialisation du fichier de configuration .env...
        copy "%~dp0.env.example" "%~dp0.env" >nul
    )
)

echo.
echo ====================================================================
echo  [✓] INSTALLATION TERMINÉE AVEC SUCCÈS !
echo  Vous pouvez maintenant lancer l'application avec :
echo    - Soit en double-cliquant sur start.bat
echo    - Soit en exécutant la commande : py start.py
echo ====================================================================
pause
