#!/usr/bin/env bash
# AutoInsta - macOS Startup Script

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(cd "$DIR/../.." >/dev/null 2>&1 && pwd)"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[!] Error: Python is not found on your Mac."
    echo "    Please install Python 3.10+ (e.g. brew install python3)."
    exit 1
fi

"$PYTHON_CMD" "$PROJECT_ROOT/scripts/server_launcher.py" "$@"
