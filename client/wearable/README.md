# AutoInsta - Wearable & Smartwatch Integration Guide

This guide explains how to connect your wearable devices (smartwatches, fitness trackers) to the AutoInsta server for heart rate telemetry and emergency Dead Man's Switch monitoring.

---

## 1. How It Works

The AutoInsta server exposes a lightweight REST API to receive health telemetry:
- **HTTP Endpoint**: `POST http://<PC_LOCAL_IP>:8000/api/sensors/health`
- **JSON Payload Format**:
  ```json
  {
    "heart_rate": 78,
    "location": "Home / Watch",
    "steps": 5120
  }
  ```

If heart rate drops below `hr_min_bpm` (e.g. 45 BPM) or exceeds `hr_max_bpm` (e.g. 145 BPM), the **Dead Man's Switch** automatically engages:
1. 10-second countdown with sound and vibration alerts.
2. The user can cancel the alert at any time via the web dashboard or mobile notification.
3. If the countdown expires without response, an emergency SOS dispatch is triggered according to your configured notification channels (Android SMS, Telegram, or Webhook).

---

## 2. Test Immediately with the Simulator

Test health data reception without requiring a physical watch:
```bash
# Test normal baseline rhythm
python client/wearable/simulate_wearable.py --bpm 72

# Test tachycardia emergency trigger
python client/wearable/simulate_wearable.py --emergency tachy

# Test bradycardia emergency trigger
python client/wearable/simulate_wearable.py --emergency brady
```

---

## 3. Connecting a Physical Smartwatch

### Option A: Gadgetbridge (Recommended for open smartwatches / Android)
[Gadgetbridge](https://gadgetbridge.org/) is an open-source Android app for fitness trackers and watches (Pebble, Amazfit, Mi Band, Fossil, Garmin, Casio...).
- Gadgetbridge broadcasts Android Intents upon every heart rate sample.
- Termux or Tasker can capture these Intents and forward them to `POST /api/sensors/health`.

### Option B: Wear OS (Pixel Watch, Galaxy Watch...)
- Install the free **HTTP Shortcuts** app on Wear OS or on your connected Android phone.
- Configure an automatic webhook triggered by high/low heart rate readings pointing to `http://<PC_LOCAL_IP>:8000/api/sensors/health`.

### Option C: Apple Watch
- Use the built-in **Shortcuts** app on iOS / watchOS.
- Set up an automation: *"When heart rate rises above 140"* -> Action *"Get Contents of URL"* (`POST /api/sensors/health`).
