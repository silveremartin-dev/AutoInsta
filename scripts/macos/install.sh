#!/usr/bin/env bash
# AutoInsta - macOS Dependency Installer

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(cd "$DIR/../.." >/dev/null 2>&1 && pwd)"

echo "===================================================================="
echo "           AUTOINSTA - MACOS DEPENDENCY INSTALLER"
echo "===================================================================="

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[!] Error: Python is not found."
    exit 1
fi

echo "[*] Installing packages from requirements.txt..."
"$PYTHON_CMD" -m pip install --upgrade pip
"$PYTHON_CMD" -m pip install -r "$PROJECT_ROOT/requirements.txt"

if [ ! -f "$PROJECT_ROOT/.env" ] && [ -f "$PROJECT_ROOT/.env.example" ]; then
    echo "[*] Initializing .env file..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
fi

chmod +x "$DIR/start.sh"

echo ""
echo "===================================================================="
echo " [✓] INSTALLATION COMPLETED SUCCESSFULLY!"
echo " To start AutoInsta, run: ./scripts/macos/start.sh"
echo "===================================================================="
