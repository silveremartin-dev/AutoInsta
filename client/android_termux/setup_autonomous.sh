#!/data/data/com.termux/files/usr/bin/bash
# ========================================================
# AutoInsta - 1-Click Autonomous Setup for Android Termux
# ========================================================
set -e

echo "=============================================="
echo " AutoInsta Autonomous Setup for Android       "
echo "=============================================="

export DEBIAN_FRONTEND=noninteractive
echo "[1/4] Updating Termux repositories..."
pkg update -y -o Dpkg::Options::="--force-confold"

echo "[2/4] Installing required system packages..."
pkg install -y -o Dpkg::Options::="--force-confold" python python-cryptography openssl termux-api jq git libjpeg-turbo clang

# In Termux, pip is system-managed. Do not run 'pip install --upgrade pip'.
# Enable global flag to allow installation:
export PIP_BREAK_SYSTEM_PACKAGES=1

echo "[3/4] Installing Python dependencies..."
# Install precompiled pydantic-core wheel for Android/Termux (avoids Rust build)
echo "[*] Installing precompiled pydantic-core wheel for Android..."
pip install --break-system-packages pydantic-core --extra-index-url https://eutalix.github.io/android-pydantic-core/ --extra-index-url https://termux-user-repository.github.io/pypi/ || true

# Install all remaining Python dependencies
pip install --break-system-packages --extra-index-url https://eutalix.github.io/android-pydantic-core/ --extra-index-url https://termux-user-repository.github.io/pypi/ fastapi uvicorn requests jinja2 python-multipart pydantic google-generativeai pyyaml python-dotenv

echo "[4/4] Setting up 1-click home screen shortcuts..."
mkdir -p "$HOME/.shortcuts"
cp "$HOME/AutoInsta/client/android_termux/widget_start.sh" "$HOME/.shortcuts/AutoInsta_START.sh"
cp "$HOME/AutoInsta/client/android_termux/widget_stop.sh" "$HOME/.shortcuts/AutoInsta_STOP.sh"
chmod +x "$HOME/.shortcuts/"*.sh
chmod +x "$HOME/AutoInsta/client/android_termux/"*.sh

echo ""
echo "=========================================================="
echo " [✓] Installation completed successfully!"
echo " To start AutoInsta in autonomous mode, run:"
echo "   bash client/android_termux/run_autonomous.sh"
echo "=========================================================="
