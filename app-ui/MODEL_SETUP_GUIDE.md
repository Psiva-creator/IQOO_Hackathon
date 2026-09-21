# On-Device SLM Setup & Deployment Guide for Android / iQOO

This guide provides instructions for **Member A** to deploy and run the **Local Small Language Model (SLM)** on a physical iQOO smartphone (or ARM64 emulator).

The local AI model layer integrates with the app's task tracker and insight engine to provide real-time, explainable, natural-language coaching with **zero cloud dependencies** and **zero network requests**.

---

## 1. System Requirements & Prerequisites

| Requirement | Specification | Notes |
| :--- | :--- | :--- |
| **JDK Version** | **Java 17** (LTS) or Java 21 | Required by Android Gradle Plugin 9.x and Kotlin 2.2. Ensure `JAVA_HOME` points to JDK 17+. |
| **Android SDK** | **Android SDK Platform 34+** (compileSdk 37) | Installed via Android Studio SDK Manager (`platforms;android-34` or `platforms;android-35`). |
| **Build Tools** | **34.0.0** or 35.0.0 | Set in SDK Manager. |
| **Platform Tools / ADB** | **v34.0.0+** | Required for pushing model binaries and debugging over USB. |
| **Gradle** | **Gradle 8.11+** / **AGP 9.4.1** | Provided via project `./gradlew` wrapper. |
| **Target Device** | Physical **iQOO** phone (ARM64-v8a) | Minimum 6 GB RAM (8 GB+ recommended, e.g. iQOO 9/11/12/Neo/Z series). |
| **Minimum OS** | **Android 8.0 (API Level 26)** or higher | `minSdk = 24` is configured in `app/build.gradle.kts`. |
| **Device Free Storage** | **At least 2.5 GB free** | For storing the INT4 model bundle and runtime cache. |
| **Device Free RAM** | **At least 1.5 GB available RAM** | Required by LiteRT / MediaPipe during active 2B parameter generation. |

---

## 2. Model Format & Supported Models

The Android runtime uses **Google MediaPipe GenAI (LiteRT)** tasks. It requires pre-converted, INT4-quantized FlatBuffer task bundles (`.bin` or `.task`).

> [!IMPORTANT]
> **Do NOT use raw HuggingFace PyTorch weights (`.safetensors` or `.pt`) on Android directly.**  
> MediaPipe requires the quantized `.bin` or `.task` format that bundles the LiteRT graph and SentencePiece tokenizer.

### Recommended Models:
1. **Gemma-2B-IT CPU INT4** (Recommended for iQOO 8GB+ RAM):
   - Filename: `gemma-2b-it-cpu-int4.bin` or `gemma-2b-it-cpu-int4.task`
   - File Size: ~1.35 GB
   - Prompt Template: `gemma` (`<start_of_turn>user...`)
   - Latency on iQOO Snapdragon 8 / Dimensity: ~800ms – 2500ms
2. **TinyLlama-1.1B-Chat CPU INT4** (Lightweight alternative):
   - Filename: `tinyllama-1.1b-chat-cpu-int4.bin`
   - File Size: ~650 MB
   - Prompt Template: `tinyllama` (`<|system|>...`)
   - Latency on iQOO: ~400ms – 1200ms

> [!NOTE]
> All model weights (`*.bin`, `*.task`, `*.safetensors`, `models/`) are strictly ignored in `.gitignore`. **Never commit model weights to Git.**

---

## 3. Step-by-Step Deployment Guide

### Step 1: Connect Your Physical iQOO Device
1. On your iQOO phone, open **Settings > About Phone > Software Info** and tap **Build Number** 7 times to enable Developer Options.
2. Go to **Settings > System > Developer Options** and enable:
   - **USB Debugging**
   - **Install via USB**
3. Connect the phone to your development machine with a USB cable.
4. Verify connection in your terminal:
   ```bash
   adb devices
   ```
   *(You should see your iQOO device listed as `device`, not `unauthorized`.)*

---

### Step 2: Push Model Weights to the Device
Push the quantized model to the staging directory or app internal storage:

```bash
# Option A: Push to staging path (Standard during development)
adb push /path/to/gemma-2b-it-cpu-int4.bin /data/local/tmp/gemma-2b-it-cpu-int4.bin
adb shell chmod 644 /data/local/tmp/gemma-2b-it-cpu-int4.bin

# Option B: Push directly into app internal storage (Production/Isolated)
adb push /path/to/gemma-2b-it-cpu-int4.bin /sdcard/Download/gemma-2b-it-cpu-int4.bin
```

---

### Step 3: Verify Gradle Dependency
The MediaPipe GenAI library is declared in `app-ui/gradle/libs.versions.toml`:
```toml
[versions]
mediapipeGenai = "0.10.14"

[libraries]
mediapipe-tasks-genai = { module = "com.google.mediapipe:tasks-genai", version.ref = "mediapipeGenai" }
```

And in `app-ui/app/build.gradle.kts`:
```kotlin
dependencies {
    // ...
    implementation(libs.mediapipe.tasks.genai)
}
```

---

### Step 4: Initialize and Run in Android Code

In your Activity or ViewModel:

```kotlin
import com.iqoo.productivityai.ai.LocalAIModelFactory
import com.iqoo.productivityai.ai.ModelConfig
import com.iqoo.productivityai.ai.AIModelInput

// 1. Configure the on-device SLM
val config = ModelConfig(
    minFreeRamMb = 400L,       // Safety threshold to protect device responsiveness
    timeoutMs = 10000L,        // 10s maximum generation window
    template = "gemma",        // "gemma" or "tinyllama"
    candidatePaths = listOf(   // Optional fallback search paths
        "/data/local/tmp/gemma-2b-it-cpu-int4.bin",
        context.filesDir.resolve("models/gemma-2b-it-cpu-int4.bin").absolutePath
    )
)

// 2. Instantiate via Factory
val aiModel = LocalAIModelFactory.getModel(
    context = context,
    provider = "mediapipe",
    config = config
)

// 3. Generate natural-language coaching from structured evidence
val evidence = mapOf(
    "currentTask" to "coding",
    "productivityScore" to 42,
    "fatigue" to 78,
    "fatigueLevel" to "HIGH",
    "distraction" to 65,
    "contextSwitches" to 7,
    "context" to "Home Office",
    "riskLevel" to "HIGH",
    "confidence" to "HIGH"
)

val response = aiModel.generateCoaching(evidence)

// 4. Access structured output
println("Provider: ${response.provider}")       // e.g. "mediapipe-gemma-2b-local"
println("Is Fallback: ${response.isFallback}")  // false when live SLM runs
println("Message: ${response.message}")         // "You're showing signs of fatigue..."
println("Action: ${response.action}")           // "Take a short 10-minute break..."
println("Latency: ${response.latencyMs} ms")
```

---

## 4. Automatic 4-Tier Fallback Protection

The integration layer guarantees that the Android UI will **never crash** or hang, even if hardware constraints or model file issues arise:

| Tier | Failure Condition | Behavior | Returned Provider Metadata |
| :--- | :--- | :--- | :--- |
| **Tier 1** | Model file not found on disk | Bypasses native inference instantly; executes deterministic rule engine. | `mediapipe-gemma-2b-local (fallback: weights not installed)` |
| **Tier 2** | Available RAM < `minFreeRamMb` (400 MB) | Aborts model allocation to prevent Android OS OOM process termination. | `mediapipe-gemma-2b-local (fallback: low RAM 280MB < 400MB)` |
| **Tier 3** | Generation time > `timeoutMs` (10s) | Terminates worker thread; returns instant heuristic advice. | `mediapipe-gemma-2b-local (fallback: inference timeout > 10000ms)` |
| **Tier 4** | Native LiteRT crash / Malformed JSON | Intercepts exception; falls back gracefully. | `mediapipe-gemma-2b-local (fallback: malformed SLM output)` |

---

## 5. Building & Testing

### Running Unit Tests (on Machine with JDK installed)
```bash
cd app-ui
./gradlew testDebugUnitTest
```

### Installing APK on Connected iQOO Phone
```bash
cd app-ui
./gradlew installDebug
```

### Monitoring Inference via Logcat
```bash
adb logcat -s ProductivityAI MediaPipe LocalAIModel
```
