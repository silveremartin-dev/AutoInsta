#!/data/data/com.termux/files/usr/bin/bash
# ========================================================
# AutoInsta - Setup 1-Clic Mode Autonome sur Termux
# ========================================================
set -e

echo "=============================================="
echo " Installation d'AutoInsta Autonome sur Android"
echo "=============================================="

echo "[1/4] Mise à jour des dépôts Termux..."
pkg update -y

echo "[2/4] Installation des paquets système requis..."
pkg install -y python python-pip termux-api jq git libjpeg-turbo

echo "[3/4] Installation des librairies Python..."
pip install --upgrade pip
pip install fastapi uvicorn requests jinja2 python-multipart pydantic google-generativeai

echo "[4/4] Configuration des raccourcis Widget 1-clic..."
mkdir -p "$HOME/.shortcuts"
cp "$HOME/AutoInsta/client/android_termux/widget_start.sh" "$HOME/.shortcuts/AutoInsta_START.sh"
cp "$HOME/AutoInsta/client/android_termux/widget_stop.sh" "$HOME/.shortcuts/AutoInsta_STOP.sh"
chmod +x "$HOME/.shortcuts/"*.sh
chmod +x "$HOME/AutoInsta/client/android_termux/"*.sh

echo ""
echo "=========================================================="
echo " [✓] Installation réussie !"
echo " Pour démarrer en 1 clic :"
echo "   bash client/android_termux/run_autonomous.sh"
echo " Ou via le widget Android sur votre écran d'accueil !"
echo "=========================================================="
