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

## 🚀 Quick Start

### 1. Installation & Start on PC (Windows, macOS, Linux)

AutoInsta provides **1-click installation and startup scripts**:

#### Windows:
- **Installation** : Double-cliquez sur [`install.bat`](file:///c:/Silvere/Encours/Developpement/AutoInsta/install.bat) ou lancez `install.bat`
- **Démarrage** : Double-cliquez sur [`start.bat`](file:///c:/Silvere/Encours/Developpement/AutoInsta/start.bat) ou tapez `start.bat`
- **Menu interactif** : Propose le démarrage du serveur, le mode démo, le client webcam PC, la suite de tests, et l'autodémarrage.

#### macOS & Linux:
```bash
chmod +x install.sh start.sh
./install.sh       # Installe les dépendances Python
./start.sh         # Lance le serveur et ouvre l'interface web
```

#### Lanceur Python Universel (Multi-plateforme):
```bash
# Lancement direct (ouvre automatiquement votre navigateur sur http://localhost:8000)
python start.py

# Lancement en mode Démo / Simulation (injecte des photos et métriques de test toutes les 25s)
python start.py --mode demo

# Lancement du client webcam PC (prise de photos via la caméra de votre ordinateur)
python start.py --mode cam

# Lancement de la suite complète de tests de validation
python start.py --mode test
```

### 2. Accès à l'Interface Web & Dashboard

Une fois le serveur démarré :
- **Sur votre PC** : Ouvrez **`http://localhost:8000`**
- **Sur votre smartphone / montre (même Wi-Fi)** : Ouvrez **`http://<IP_DU_PC>:8000`** (l'IP locale est automatiquement affichée au lancement du serveur).


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
