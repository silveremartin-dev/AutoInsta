# AutoInsta (AutoInsta-POV)

> **Zero-Cost Egocentric Lifelogging & Autonomous Social Ingestion Agent**  
> Powered by **Gemini 1.5 Flash**, Multimodal Vision-Language Inference, and Automated Instagram Injection.

[![GitHub Repo](https://img.shields.io/badge/GitHub-silveremartin--dev%2FAutoInsta-blue?logo=github)](https://github.com/silveremartin-dev/AutoInsta)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini 1.5 Flash](https://img.shields.io/badge/Gemini-1.5%20Flash-4285F4.svg?logo=google)](https://aistudio.google.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Concept: The Zahavi Bypass

In evolutionary sociology, **Zahavi's Costly Signaling Theory** posits that social validation depends on finite attention and metabolic cost (curating moments, framing shots, drafting captions, managing social presence).

**AutoInsta** short-circuits this transaction through **algorithmic Batesian mimicry**:
1. **Passive Optical Capture**: Your Android smartphone (in a shirt pocket, chest harness, or lanyard) or smart glasses opportunistically capture first-person point-of-view (POV) images during your day.
2. **Autonomous VLM Curation**: Google **Gemini 1.5 Flash** inspects the raw visual stream, eliminates private screens and blurry shots, rates social/aesthetic interest (0–10), and composes context-aware Instagram captions in your selected persona.
3. **Automated Social Injection**: If the frame exceeds the aesthetic threshold and cooldown limits, AutoInsta seamlessly publishes it to Instagram—generating genuine social presence with **zero cognitive overhead**.

---

## 🏗️ Architecture

```
                                  [ Android Smartphone / POV Rig ]
                                     (Termux / CameraX / Wearable)
                                                 │
                             1 frame / 30-60s    │  (Gated by Light & Motion sensors)
                                                 ▼
                                     [ AutoInsta Server (FastAPI) ]
                                                 │
                                                 ▼
                                     [ Multimodal VLM (Gemini 1.5 Flash) ]
                                     ├── Privacy / Safety Filter (Screens, IDs, Intimate scenes)
                                     ├── Quality Gate (Clarity & Exposure)
                                     ├── Aesthetic Scoring (0.0 to 10.0)
                                     └── Persona Narrative & Hashtag Synthesis
                                                 │
                                  Score >= 7.0 & Safety Pass
                                                 │
                                                 ▼
                                     [ Instagram Publisher ]
                                     ├── Dry-Run Mode (Preview & Simulation)
                                     ├── Instagrapi Engine (Direct Mobile Emulation)
                                     └── Meta Graph API (Official Creator / Business)
                                                 │
                                                 ▼
                                       [ Live Instagram Feed / Story ]
```

---

## ✨ Features

- 📸 **Multi-Source Ingestion**:
  - **Android Phones**: Direct lifelogging via Termux / Termux:API (under 2-minute setup) or native Kotlin background service.
  - **Smart Wearables / Glasses**: Brilliant Labs Frame, OpenGlass, ESP32-CAM, or RTSP feeds.
  - **Python Camera Client**: Desktop webcams, OBS virtual cameras, or DroidCam streams with motion-difference filtering.
- 🧠 **Gemini 1.5 Flash Multimodal Pipeline**:
  - **Privacy Shield**: Auto-redacts screens with sensitive text, credit cards, banking info, and private rooms.
  - **Aesthetic Scoring**: Evaluates composition, lighting, novelty, and urban/natural serendipity.
  - **Persona-Calibrated Captions**: Choose between `spontaneous_chic`, `witty_minimalist`, `candid_existential`, `poetic_flaneur`, or `tech_nomad`.
- 🚀 **Instagram Action Engine**:
  - `dry_run` mode for risk-free local testing and UI review.
  - `instagrapi` mobile API wrapper with session persistence and anti-ban delays.
  - Official Meta Graph API support for Creator/Business accounts.
  - Anti-spam cooldown rules (configurable post frequency and daily limits).
- 🖥️ **Live Web Dashboard**:
  - Real-time POV stream gallery, visual metrics, VLM reasoning breakdown, and manual one-click publishing.

---

## 🚀 Quick Start

### 1. Clone & Install Server

```bash
git clone https://github.com/silveremartin-dev/AutoInsta.git
cd AutoInsta

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your Gemini API key:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Get your free key at https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Publisher mode: dry_run | instagrapi | meta_graph
PUBLISH_MODE=dry_run

# Optional credentials if PUBLISH_MODE=instagrapi
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

### 3. Run the AutoInsta Server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` in your browser to view the **AutoInsta Dashboard**.

---

## 📱 Android Client Setup (Termux Lifelogger)

You can turn any Android phone into an autonomous POV camera in **2 minutes**:

1. Install **Termux** and **Termux:API** from [F-Droid](https://f-droid.org/).
2. Grant Camera and Sensor permissions to Termux:API.
3. Open Termux on your phone and run:

```bash
pkg update && pkg install -y python termux-api git
pip install requests

# Download capture script
curl -O https://raw.githubusercontent.com/silveremartin-dev/AutoInsta/main/client/android_termux/autoinsta_capture.py

# Configure server IP (your PC's local Wi-Fi IP or Tailscale IP)
export AUTOINSTA_SERVER="http://192.168.1.50:8000/api/capture/upload"
export AUTOINSTA_INTERVAL="30" # capture every 30 seconds

# Start capture loop
python autoinsta_capture.py
```

*The Termux client automatically reads the phone's light sensor: if the phone is tucked in a dark pocket or face-down, it pauses capture to conserve battery!*

---

## 💻 Python Desktop / Webcam Client

To test with a computer webcam, USB camera, or RTSP feed:

```bash
python client/python_cam/cam_client.py --server http://localhost:8000/api/capture/upload --camera 0 --interval 30
```

Options:
- `--camera 0`: Index of webcam or RTSP URL (`rtsp://...`)
- `--interval 30`: Capture every 30 seconds
- `--no-motion`: Disable the frame difference motion gate

---

## ⚙️ Configuration Reference (`config.yaml`)

```yaml
vlm:
  model: "gemini-1.5-flash"
  temperature: 0.7
  min_social_score: 7.0         # Minimum score (0-10) to auto-publish
  require_safety_pass: true      # Privacy shield
  require_quality_pass: true     # Blur and darkness check
  persona: "spontaneous_chic"   # Caption style
  language: "en"                 # Language code

publisher:
  mode: "dry_run"               # "dry_run", "instagrapi", or "meta_graph"
  target_type: "feed"           # "feed" or "story"
  min_interval_minutes: 60      # Cooldown between posts
  max_daily_posts: 4            # Daily post limit
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/capture/upload` | Ingest POV frame (`multipart/form-data`) |
| `GET` | `/api/captures` | List captures with VLM evaluation & status |
| `GET` | `/api/captures/{id}` | Get specific capture details & reasoning |
| `POST` | `/api/captures/{id}/publish` | Manually force-publish a capture |
| `POST` | `/api/captures/{id}/reevaluate` | Trigger VLM re-evaluation |
| `GET` | `/api/stats` | Ingestion & social publishing statistics |
| `GET` / `POST` | `/api/config` | View or update runtime settings |

---

## 📜 Agent Guidelines

See [AGENT.md](AGENT.md) for full architectural guidelines, prompt engineering patterns, and autonomous lifecycle specifications.

---

## ⚖️ License

Distributed under the **MIT License**. See `LICENSE` for details.
