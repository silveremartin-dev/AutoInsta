#!/usr/bin/env bash
# AutoInsta - macOS Dependency Installer

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(cd "$DIR/../.." >/dev/null 2>&1 && pwd)"

echo "===================================================================="
echo "           AUTOINSTA - INSTALLATION DES DÉPENDANCES MACOS"
echo "===================================================================="

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[!] Erreur : Python est introuvable."
    exit 1
fi

echo "[*] Installation des paquets depuis requirements.txt..."
"$PYTHON_CMD" -m pip install --upgrade pip
"$PYTHON_CMD" -m pip install -r "$PROJECT_ROOT/requirements.txt"

if [ ! -f "$PROJECT_ROOT/.env" ] && [ -f "$PROJECT_ROOT/.env.example" ]; then
    echo "[*] Initialisation du fichier .env..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
fi

chmod +x "$DIR/start.sh"

echo ""
echo "===================================================================="
echo " [✓] INSTALLATION TERMINÉE AVEC SUCCÈS !"
echo " Pour démarrer AutoInsta, lancez : ./scripts/macos/start.sh"
echo "===================================================================="
