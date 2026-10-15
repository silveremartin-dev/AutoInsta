# Native Android Client (Kotlin + Jetpack Compose)

This directory hosts the native Android client for **AutoInsta**. It can be generated, prototyped, and updated using **Google AI Studio (Build Mode -> Android)** or developed locally via Android Studio.

---

## 🛠️ Rapid Generation & Prototyping via Google AI Studio

Google AI Studio allows prompt-to-app generation for native Android projects (Kotlin + Jetpack Compose) with zero local SDK configuration.

### Deployment & Distribution Channels

1. **Direct WebUSB Installation ("Install on Device")**:
   - Plug your Android device into your PC via USB.
   - Click **Install on Device** in Google AI Studio (Chrome / Edge).
   - The compiled APK is pushed directly onto your phone without requiring manual ADB setup.
2. **Google Play Console Internal Testing Track**:
   - Under `Settings > Publish`, deploy directly to your **Internal Testing** track (supporting up to 100 invited testers via Gmail).
   - *Note*: General public Play Store distribution is restricted by Google due to strict background camera privacy rules (`FOREGROUND_SERVICE_CAMERA`).
3. **GitHub Versioning & Local Export**:
   - Download the project archive (**Export / Download ZIP**) from AI Studio.
   - Extract the standard Gradle structure directly into this folder (`client/android/`).
   - Commit and push to GitHub:
     ```bash
     git add client/android/
     git commit -m "feat(android): update native client from Google AI Studio build"
     git push
     ```

---

## 🏗️ Architectural Options

AutoInsta supports two architectural directions for Android:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MODE 1: COMPANION CLIENT                        │
│                   (Recommended - Zero Backend Rewrite)                 │
└────────────────────────────────────────────────────────────────────────┘
 [ Android Phone: CameraX + Gating ] ──(HTTP POST)──► [ FastAPI Backend ]
                                                             │
                                                             ▼
                                                    [ Gemini 1.5 Flash ]
                                                             │
                                                             ▼
                                                    [ Instagrapi Worker ]

┌────────────────────────────────────────────────────────────────────────┐
│                 MODE 2: STANDALONE EDGE AGENT (ROADMAP)                │
│                         (100% Mobile, No Server)                       │
└────────────────────────────────────────────────────────────────────────┘
 [ Android Phone: CameraX + Gating ]
         │
         ├── Google Generative AI Android SDK ──► [ Gemini 1.5 Flash ]
         │   (Subsidized via AI Studio Free Tier: 1,500 req/day)
         │
         └── Android Share Intent (ACTION_SEND) ──► [ Instagram App ]
             (Zero risk of account ban, no private API scraping)
```

---

### Mode 1: Companion Client (Current / Production)

The Android app acts strictly as an edge sensor and camera buffer, offloading curation, database storage, and Instagram injection to your existing AutoInsta FastAPI server.

#### Prompt for Google AI Studio (Mode 1):
```text
Build a native Android lifelogging client app for "AutoInsta" in Kotlin with Jetpack Compose.

Features required:
1. UI / Settings:
   - Server URL input (e.g. http://192.168.1.50:8000)
   - Capture interval slider (30s to 300s, default 60s)
   - Toggle switches: Camera, GPS tracking, Accelerometer gating, Light sensor pocket detection
   - Start / Stop Lifelogging toggle with visual status (Green = Active, Grey = Paused)
   - Live preview showing the last captured thumbnail and upload status (HTTP 200 / Error).

2. Background Foreground Service:
   - Persistent ForegroundService with notification controls (Start / Stop).
   - CameraX ImageCapture takes photos at the configured interval.
   - Sensor Gating:
     * Suppress capture if light sensor reads < 5 lux (in pocket/bag).
     * Suppress capture if significant motion is not detected since last shot.
   - Attach current GPS latitude, longitude, and speed (km/h) to metadata.

3. Networking:
   - Upload captured photos via multipart/form-data to POST "{server_url}/api/capture/upload"
   - Fields: file (image/jpeg), latitude (float), longitude (float), speed (float).
   - Graceful offline handling: retry on failure.

4. Permissions:
   - Request CAMERA, ACCESS_FINE_LOCATION, FOREGROUND_SERVICE, FOREGROUND_SERVICE_CAMERA.
```

---

### Mode 2: Standalone Edge Agent (Roadmap Exploration)

For users who want zero server setup, the app runs entirely on the smartphone:
- **Cost**: 100% subsidized by Google AI Studio's Free Tier (up to 1,500 requests/day on `gemini-1.5-flash`).
- **Posting**: Triggers an Android notification when a candidate score is $\ge 7.5$. Tapping it launches the official Instagram app with the image and auto-copied caption via `Intent.ACTION_SEND`.

#### Prompt for Google AI Studio (Mode 2):
```text
Build a standalone native Android app in Kotlin with Jetpack Compose called "AutoInsta Standalone".

1. Direct Gemini Integration:
   - Use Google Generative AI Android SDK ("com.google.ai.client.generativeai:generativeai").
   - Include a Settings field to enter and store the Google AI Studio API Key.
   - Use model "gemini-1.5-flash".

2. Background Foreground Service:
   - Persistent ForegroundService with notification ("AutoInsta Active").
   - CameraX background capture every N seconds (configurable 30s-300s).
   - Suppress capture if ambient light < 5 lux or phone is motionless.

3. On-Device Evaluation:
   - Send captured bitmap to Gemini with system instructions to verify privacy (safety_pass) and evaluate social_score (0.0 to 10.0) + caption.

4. Instagram Action:
   - If safety_pass == true and social_score >= 7.5:
     * Post a notification: "High quality capture found! Score: {score}".
     * Tapping notification fires Intent.ACTION_SEND targeting "com.instagram.android" with image URI and copies caption to clipboard.
   - Store past evaluations in local Room DB for a History tab.
```

---

## 📂 Expected Directory Structure

When exported from Google AI Studio or built with Gradle:

```
client/android/
├── app/
│   ├── src/main/
│   │   ├── java/dev/silveremartin/autoinsta/
│   │   │   ├── MainActivity.kt               # Jetpack Compose UI
│   │   │   ├── service/
│   │   │   │   └── LifelogCaptureService.kt  # CameraX ForegroundService
│   │   │   ├── sensors/
│   │   │   │   └── MotionSensorManager.kt    # Accelerometer & Light gating
│   │   │   └── network/
│   │   │       └── AutoInstaApiClient.kt     # Retrofit / OkHttp uploader
│   │   └── AndroidManifest.xml
│   └── build.gradle.kts
├── settings.gradle.kts
└── build.gradle.kts
```
