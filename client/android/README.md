# Native Android Lifelogging Service (Kotlin + CameraX)

For a fully native Android APK running as a persistent `ForegroundService` with notification controls, sensor fusion (accelerometer + proximity + light sensor), and CameraX background capture.

---

### Architecture Overview

```
client/android/
├── app/
│   ├── src/main/java/dev/silveremartin/autoinsta/
│   │   ├── MainActivity.kt               # Permission granting & server URL configuration UI
│   │   ├── service/
│   │   │   └── LifelogCaptureService.kt  # Foreground Service with CameraX lifecycle
│   │   ├── sensors/
│   │   │   └── MotionSensorManager.kt    # Significant motion and light sensor gating
│   │   └── network/
│   │       └── AutoInstaApiClient.kt     # Retrofit / OkHttp multipart uploader
│   └── AndroidManifest.xml
```

---

### Key Components

#### 1. Sensor Gating
- `Sensor.TYPE_SIGNIFICANT_MOTION` / `TYPE_LINEAR_ACCELERATION`: Triggers frame capture only when the user is moving through space or interacting with the world.
- `Sensor.TYPE_LIGHT` & `Sensor.TYPE_PROXIMITY`: Immediately suppresses capture when phone is in a pocket, bag, or facing down on a table.

#### 2. CameraX ImageCapture
- Captures JPEG buffers directly into memory without requiring an active UI viewfinder.
- Downscales / optimizes compression before upload to conserve mobile bandwidth and battery.

#### 3. Network Transport
- Streams image buffers to `POST /api/capture/upload` with retry logic and offline queueing if network drops.
