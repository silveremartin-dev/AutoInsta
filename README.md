# AutoInsta (AutoInsta-POV)

> **Zero-Cost Egocentric Lifelogging, Multi-Sensor Agent & Instagram Ingestion**  
> Powered by **Gemini 1.5 Flash**, Multimodal Vision-Language Inference, Sensor Fusion, and Human-in-the-Loop Approval.

[![GitHub Repo](https://img.shields.io/badge/GitHub-silveremartin--dev%2FAutoInsta-blue?logo=github)](https://github.com/silveremartin-dev/AutoInsta)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini 1.5 Flash](https://img.shields.io/badge/Gemini-1.5%20Flash-4285F4.svg?logo=google)](https://aistudio.google.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Concept: The Zahavi Bypass

In evolutionary sociology, **Zahavi's Costly Signaling Theory** posits that authentic social validation depends on finite attention and metabolic cost (framing shots, curating memories, drafting captions, maintaining social presence).

**AutoInsta** short-circuits this transaction through **algorithmic Batesian mimicry**:
1. **Passive Multi-Sensor Capture**: Your Android smartphone (in a shirt pocket, lanyard, or mount) or PC webcam opportunistically captures point-of-view (POV) images while monitoring GPS, motion, light, and optional wearable biometric metrics.
2. **Autonomous VLM Curation**: Google **Gemini 1.5 Flash** inspects the visual stream with a **zero-tolerance privacy shield** (auto-rejecting private screens, banking, intimate spaces, and nudity), evaluates aesthetic interest (0–10), and composes context-aware Instagram captions tailored to your physical location and speed.
3. **Human-in-the-Loop or Autonomous Injection**: Review proposed posts one by one with a single click, or let the agent post automatically according to strict cooldown protocols.

---

## 🏗️ Architecture & Pipeline

```
               [ Android Phone / Wearable / PC Webcam ]
               ├── Camera (POV image buffer)
               ├── GPS & Speed (Neighborhood / City context)
               ├── Accelerometer (Movement vs static desk)
               ├── Light Sensor (Anti-pocket / bag dark filter)
               └── Optional Heart Rate BLE (BPM / Health Alert)
                                 │
                                 ▼
                     [ AutoInsta Server (FastAPI) ]
                                 │
                                 ▼
                 [ Gemini 1.5 Flash Multimodal Ingestion ]
                 ├── Strict Privacy Filter (Zero-tolerance screens & intimacy)
                 ├── Quality Gate (Clarity, exposure, blur)
                 ├── Aesthetic & Narrative Scoring (0.0 to 10.0)
                 └── Context-Aware Caption Generation (Persona + Location)
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
    [ Require Approval: TRUE ]       [ Require Approval: FALSE ]
      Stored in "Pending Queue"        Auto-posted if score >= 7.0
      User clicks: [Approve / Reject]
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                     [ Instagram Publisher ]
                     ├── Dry-Run Mode (Safe local preview)
                     ├── Instagrapi (Direct mobile API)
                     └── Meta Graph API (Official Creator/Business)
```

---

## ✨ Features & Capabilities

- 🔒 **Zero-Tolerance Privacy & Safety Gate**:
  - Automatically rejects photos containing computer/phone screens with private chats, emails, banking information, or passwords.
  - Automatically rejects nudity, swimwear, intimate reflections, bathrooms, and locker rooms.
- 🎛️ **Granular Sensor Toggles (Individual ON/OFF)**:
  - **Camera**: Enable or disable continuous image acquisition.
  - **GPS & Location**: Toggle location-aware captions and Instagram geotagging.
  - **Accelerometer**: Only shoot when actually moving; pauses when sitting still.
  - **Light Sensor**: Skips dark shots inside pockets or bags to save battery.
  - **Heart Rate & Wearable Sensor**: Optional physiological tracking (toggleable at any time).
- 🚨 **Emergency Heart Rate Alert (Experimental / Non-Medical)**:
  - Configurable high/low BPM thresholds (e.g. `< 45` or `> 145`).
  - Sends immediate emergency distress alerts via Android SMS (`termux-sms-send`), Telegram, or Webhook containing live GPS Google Maps coordinates.
- 📋 **Human-in-the-Loop Approval Queue**:
  - Review candidates one by one on the dashboard before anything goes live.
  - Edit captions inline before approving.
  - Complete chronological history showing all past captures with status (`Published`, `Pending Approval`, `Manually Rejected`, `AI Rejected`).
- 🔄 **Cross-Platform Autostart & Autostop**:
  - Works on **Windows**, **macOS**, **Linux** (systemd user service), and **Android** (Termux:Boot).
  - Single CLI command to activate, deactivate, or completely remove autostart.
- 📱 **One-Tap Phone Launcher (Termux:Widget)**:
  - Two buttons on your Android home screen: **"AutoInsta Start"** and **"AutoInsta Stop"** with instant toast feedback.

---

## 🚀 Guide de Démarrage Rapide

### ⚠️ Différence Essentielle : `INSTALL` vs `START`

| Étape | Rôle | Quand l'exécuter ? |
| :--- | :--- | :--- |
| **`INSTALL`** | Télécharge et installe les bibliothèques requises (`fastapi`, `uvicorn`, `pillow`, etc.) et initialise le fichier de configuration `.env`. | **Une seule fois**, lors de la première installation. |
| **`START`** | Démarre le serveur local, active l'écoute des capteurs, ouvre le tableau de bord web et prépare la file d'approbation. | **À chaque utilisation**, quand vous voulez faire tourner AutoInsta. |

---

### 💻 Utilisation par Plateforme (Dossier `scripts/`)

Tous les scripts ont été regroupés proprement dans le sous-dossier [`scripts/`](file:///c:/Silvere/Encours/Developpement/AutoInsta/scripts/) par système d'exploitation :

#### 🪟 Windows :
- **1. Installation initiale (1 seule fois)** :
  Double-cliquez sur [`scripts/windows/install.bat`](file:///c:/Silvere/Encours/Developpement/AutoInsta/scripts/windows/install.bat).
- **2. Lancement au quotidien** :
  Double-cliquez sur le raccourci [**`start.bat`**](file:///c:/Silvere/Encours/Developpement/AutoInsta/start.bat) à la racine du projet (ou [`scripts/windows/start.bat`](file:///c:/Silvere/Encours/Developpement/AutoInsta/scripts/windows/start.bat)).
- **Menu interactif proposé** :
  ```text
  [1] Démarrer le Serveur Web & Ouvrir le Tableau de bord (Recommandé)
  [2] Démarrer le Serveur en Mode Démo (Simulation photos & capteurs)
  [3] Lancer le Client Caméra PC (Webcam locale)
  [4] Exécuter la Suite de Tests Complète
  [5] Installer ou Mettre à jour les dépendances requises
  [6] Activer l'Autodémarrage au Boot (Windows / macOS / Linux)
  [7] Désactiver l'Autodémarrage
  ```

#### 🐧 Linux :
```bash
# 1. Installation initiale (1 seule fois)
./scripts/linux/install.sh

# 2. Lancement au quotidien
./scripts/linux/start.sh
```

#### 🍏 macOS :
```bash
# 1. Installation initiale (1 seule fois)
./scripts/macos/install.sh

# 2. Lancement au quotidien
./scripts/macos/start.sh
```

---

### 🌐 Accès à l'Interface Web & Dashboard

Dès que le serveur est démarré :
- **Sur votre ordinateur** : Accédez à [**`http://localhost:8000`**](http://localhost:8000)
- **Sur votre téléphone / montre connectée (même réseau Wi-Fi)** : Accédez à **`http://<IP_DU_PC>:8000`** *(l'adresse IP locale de votre machine est affichée automatiquement dans la console au démarrage).*



---

## ⚡ Autostart & Autostop Setup

Enable or remove AutoInsta on boot across all operating systems with a single command:

```bash
# Enable autostart on system boot
python scripts/autostart/manage_autostart.py --enable

# Disable and completely remove autostart
python scripts/autostart/manage_autostart.py --disable
```

- **Windows**: Places a batch shortcut in `shell:startup`.
- **macOS**: Registers a LaunchAgent in `~/Library/LaunchAgents/`.
- **Linux**: Creates and activates a systemd user service (`~/.config/systemd/user/autoinsta.service`).
- **Android**: Installs a boot trigger script in `~/.termux/boot/`.

---

## 📱 Android Client Setup (Termux + Home Screen Widget)

Turn your Android phone into an autonomous POV camera with 2 home screen icons:

1. Install **Termux**, **Termux:API**, and **Termux:Widget** from [F-Droid](https://f-droid.org/).
2. Grant Camera, Location, and Sensor permissions in Android Settings.
3. Open Termux on your phone and run:

```bash
pkg update && pkg install -y python termux-api git
pip install requests

# Clone repository
git clone https://github.com/silveremartin-dev/AutoInsta.git
cd AutoInsta

# Setup Home Screen Widgets
mkdir -p ~/.shortcuts
cp client/android_termux/widget_start.sh ~/.shortcuts/AutoInsta_ON
cp client/android_termux/widget_stop.sh ~/.shortcuts/AutoInsta_OFF
chmod +x ~/.shortcuts/*
```

4. Long-press on your phone's home screen, add the **Termux:Widget**, and select **AutoInsta_ON** and **AutoInsta_OFF**. You now have one-touch activation directly on your home screen!

---

## ⚙️ Configuration Reference (`config.yaml`)

```yaml
sensors:
  enable_camera: true
  enable_gps: true
  enable_accelerometer: true
  enable_light_sensor: true
  enable_heart_rate: false           # Disabled by default
  
  heart_rate_alert:
    enabled: false
    min_bpm: 45
    max_bpm: 145
    emergency_contact: "+33600000000" # SMS or webhook recipient

publisher:
  mode: "dry_run"                    # "dry_run", "instagrapi", or "meta_graph"
  require_manual_confirmation: true  # One-by-one user approval queue
  target_type: "feed"                # "feed" or "story"
  min_interval_minutes: 60
  max_daily_posts: 4
```

---

## 📜 Agent Guidelines

See [AGENT.md](AGENT.md) for full architectural specifications, prompt heuristics, and privacy compliance guidelines.

---

## ⚖️ License

Distributed under the **MIT License**. See `LICENSE` for details.
