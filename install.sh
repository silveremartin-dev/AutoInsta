#!/usr/bin/env bash
# AutoInsta - Linux & macOS Dependency Installer

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

echo "===================================================================="
echo "           AUTOINSTA - INSTALLATION DES DÉPENDANCES PC"
echo "===================================================================="

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[!] Erreur : Python est introuvable sur votre système."
    exit 1
fi

echo "[*] Installation des dépendances via pip..."
"$PYTHON_CMD" -m pip install --upgrade pip
"$PYTHON_CMD" -m pip install -r "$DIR/requirements.txt"

if [ ! -f "$DIR/.env" ] && [ -f "$DIR/.env.example" ]; then
    echo "[*] Création du fichier .env..."
    cp "$DIR/.env.example" "$DIR/.env"
fi

chmod +x "$DIR/start.sh"

echo ""
echo "===================================================================="
echo " [✓] INSTALLATION TERMINÉE AVEC SUCCÈS !"
echo " Vous pouvez lancer AutoInsta via : ./start.sh"
echo "===================================================================="
