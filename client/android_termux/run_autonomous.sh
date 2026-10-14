#!/data/data/com.termux/files/usr/bin/bash
# ========================================================
# AutoInsta - Mode 100% Autonome Smartphone (Sans PC)
# ========================================================
# Lance le serveur FastAPI, la base SQLite locale, l'IA Gemini
# et le rig de capture caméra & capteurs directement sur Android.

termux-wake-lock
cd "$HOME/AutoInsta" || cd "/data/data/com.termux/files/home/AutoInsta"

# 1. Arrêter d'anciens processus s'ils tournent
pkill -f "autoinsta_capture.py" 2>/dev/null
pkill -f "uvicorn server.app:app" 2>/dev/null
sleep 1

# 2. Démarrage du serveur local AutoInsta sur localhost:8000
echo "[*] Démarrage du serveur local AutoInsta (FastAPI + SQLite)..."
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000 > "$HOME/autoinsta_server.log" 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "$HOME/autoinsta_server.pid"

# Attente brève pour l'initialisation du serveur
sleep 2

# 3. Démarrage du rig de capture (min-lux=5.0 anti-poche restauré)
echo "[*] Démarrage de la capture caméra & capteurs..."
python client/android_termux/autoinsta_capture.py --server http://127.0.0.1:8000/api/capture/upload --min-lux 5.0 --interval 30 > "$HOME/autoinsta_capture.log" 2>&1 &
CAPTURE_PID=$!
echo $CAPTURE_PID > "$HOME/autoinsta_capture.pid"

# 4. Feedback visuel et ouverture de l'application
termux-toast "AutoInsta Autonome Actif (localhost:8000)"
termux-open-url "http://localhost:8000"

echo "=========================================================="
echo " [✓] AutoInsta fonctionne en TOTALE AUTONOMIE sur ce smartphone !"
echo "     - Interface : http://localhost:8000"
echo "     - Serveur PID : $SERVER_PID"
echo "     - Capture PID : $CAPTURE_PID"
echo "     - Pour tout arrêter : bash client/android_termux/widget_stop.sh"
echo "=========================================================="
