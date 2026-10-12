#!/usr/bin/env bash
# AutoInsta - Linux & macOS Launcher

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# Detect python3 or python
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[!] Erreur : Python est introuvable sur votre système."
    echo "    Veuillez installer Python 3.10+ (ex: sudo apt install python3 python3-pip)."
    exit 1
fi

"$PYTHON_CMD" "$DIR/start.py" "$@"
