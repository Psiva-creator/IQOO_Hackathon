package com.iqoo.productivityai.ai

import android.content.Context
import java.io.File
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException

/**
 * Local AI Model Integration Layer for Android / iQOO devices.
 *
 * Implements Google MediaPipe GenAI (LiteRT) on-device LLM inference for Gemma-2B / TinyLlama
 * with strict privacy filtering and automatic 4-tier fallback to FallbackAIModel.
 */

/**
 * Sanitized, privacy-preserving structured evidence passed from Insight Engine.
 * Never includes raw task titles, free-text notes, GPS coordinates, URLs, or personal names.
 */
data class AIModelInput(
    val currentTask: String = "general",
    val productivityScore: Int = 50,
    val fatigue: Int = 0,
    val fatigueLevel: String = "LOW",
    val distraction: Int = 0,
    val contextSwitches: Int = 0,
    val context: String = "Home Office",
    val peakWindow: String = "09:00 - 11:00",
    val isInPeakWindow: Boolean = false,
    val prediction: Int = 50,
    val riskLevel: String = "LOW",
    val confidence: String = "MEDIUM",
    val detectedTrigger: String? = null,
    val facts: List<String> = emptyList()
) {
    companion object {
        private val ALLOWED_TASKS = setOf(
            "coding", "writing", "meeting", "reading", "planning",
            "exercise", "design", "research", "admin", "general"
        )

        private val STANDARD_CONTEXTS = setOf(
            "Home Office", "Office", "Cafe", "Library", "Meeting Room",
            "Transit", "Home", "Remote", "Focus Room"
        )

        @Suppress("UNCHECKED_CAST")
        fun fromEvidence(evidence: Map<String, Any?>): AIModelInput {
            val nested = evidence["structuredEvidence"] as? Map<String, Any?> ?: evidence

            val rawTask = (nested["currentTask"] ?: nested["taskType"] ?: "general").toString()
            val cleanTask = sanitizeTaskType(rawTask)

            val score = (nested["productivityScore"] ?: nested["score"] ?: 50) as? Number ?: 50
            val fatigueScore = (nested["fatigueScore"] ?: nested["fatigue"] ?: 0) as? Number ?: 0
            val fatigueLvl = (nested["fatigueLevel"] ?: if (fatigueScore.toInt() >= 65) "HIGH" else if (fatigueScore.toInt() >= 35) "MEDIUM" else "LOW").toString()

            val distractionScore = (nested["distractionScore"] ?: nested["distraction"] ?: 0) as? Number ?: 0
            val switches = (nested["contextSwitches"] ?: nested["recentContextSwitches"] ?: 0) as? Number ?: 0

            val rawCtx = (nested["context"] ?: nested["location"] ?: "Home Office").toString()
            val cleanCtx = sanitizeContext(rawCtx)

            val peak = (nested["peakWindow"] ?: nested["bestFocusWindow"] ?: nested["peakHour"] ?: "09:00 - 11:00").toString()
            val inPeak = (nested["isInPeakWindow"] as? Boolean) ?: false

            val pred = (nested["prediction"] ?: nested["predictedScore"] ?: score) as? Number ?: score
            val risk = (nested["riskLevel"] ?: if (pred.toInt() < 45) "HIGH" else if (pred.toInt() < 70) "MEDIUM" else "LOW").toString()
            val conf = (nested["confidence"] ?: nested["confidenceLevel"] ?: "MEDIUM").toString()
            val trigger = nested["detectedTrigger"]?.toString() ?: nested["trigger"]?.toString()

            val rawFacts = nested["facts"] as? List<*> ?: nested["evidence"] as? List<*> ?: emptyList<Any>()
            val facts = rawFacts.mapNotNull { it?.toString()?.take(120) }

            return AIModelInput(
                currentTask = cleanTask,
                productivityScore = score.toInt().coerceIn(0, 100),
                fatigue = fatigueScore.toInt().coerceIn(0, 100),
                fatigueLevel = fatigueLvl.uppercase(),
                distraction = distractionScore.toInt().coerceIn(0, 100),
                contextSwitches = switches.toInt().coerceAtLeast(0),
                context = cleanCtx,
                peakWindow = peak,
                isInPeakWindow = inPeak,
                prediction = pred.toInt().coerceIn(0, 100),
                riskLevel = risk.uppercase(),
                confidence = conf.uppercase(),
                detectedTrigger = trigger,
                facts = facts
            )
        }

        private fun sanitizeTaskType(raw: String): String {
            val lower = raw.lowercase().trim()
            for (allowed in ALLOWED_TASKS) {
                if (lower.contains(allowed)) return allowed
            }
            return "general"
        }

        private fun sanitizeContext(raw: String): String {
            val trimmed = raw.trim()
            for (std in STANDARD_CONTEXTS) {
                if (trimmed.equals(std, ignoreCase = true)) return std
            }
            return trimmed.take(30).ifBlank { "Home Office" }
        }
    }
}

/**
 * Structured coaching output conforming strictly to contracts/ai_model.schema.json.
 */
data class AIModelResponse(
    val message: String,
    val reason: String,
    val action: String,
    val confidence: String = "HIGH",
    val provider: String = "fallback",
    val isFallback: Boolean = true,
    val latencyMs: Double = 0.0
) {
    fun toMap(): Map<String, Any?> = mapOf(
        "message" to message,
        "reason" to reason,
        "action" to action,
        "confidence" to confidence,
        "provider" to provider,
        "isFallback" to isFallback,
        "latencyMs" to latencyMs
    )
}

/**
 * Local AI Model Provider interface.
 */
interface LocalAIModel {
    val modelName: String
    val isFallback: Boolean
    val isReady: Boolean get() = true

    fun generateCoaching(input: AIModelInput): AIModelResponse
    fun generateCoaching(evidence: Map<String, Any?>): AIModelResponse =
        generateCoaching(AIModelInput.fromEvidence(evidence))
}

/**
 * Deterministic offline fallback coach.
 */
class FallbackAIModel : LocalAIModel {
    override val modelName: String = "deterministic-fallback-v1"
    override val isFallback: Boolean = true

    override fun generateCoaching(input: AIModelInput): AIModelResponse {
        val startTime = System.currentTimeMillis()

        val task = input.currentTask
        val score = input.productivityScore
        val fatigue = input.fatigue
        val fatigueLvl = input.fatigueLevel
        val distraction = input.distraction
        val switches = input.contextSwitches
        val ctx = input.context
        val peak = input.peakWindow
        val isPeak = input.isInPeakWindow
        val risk = input.riskLevel
        val conf = input.confidence
        val trigger = input.detectedTrigger

        val message: String
        val reason: String
        val action: String
        val resConf: String

        // 1. Missing / Insufficient Evidence (Cold Start)
        val isInsufficient = conf == "LOW" ||
                ((trigger == null || trigger == "NONE" || trigger == "CALIBRATING" || trigger == "LOW_CONFIDENCE" || trigger == "INSUFFICIENT_DATA") &&
                (score == 0 || score == 50) && fatigue == 0 && switches == 0 && input.facts.isEmpty())

        if (isInsufficient) {
            return AIModelResponse(
                message = "Focus calibration in progress. Log your focus blocks to unlock personalized coaching.",
                reason = "Insufficient behavioral telemetry to detect detailed fatigue or context patterns.",
                action = "Track at least 5 focus sessions across different hours to calibrate your personal model.",
                confidence = "LOW",
                provider = modelName,
                isFallback = true,
                latencyMs = (System.currentTimeMillis() - startTime).toDouble()
            )
        }

        // 2. High Fatigue + Frequent Context Switching (Prompt Exemplar Rule)
        // Example: fatigue=78, contextSwitches=7, risk=HIGH
        if ((fatigue >= 65 || fatigueLvl == "HIGH") && (switches >= 5 || distraction >= 50)) {
            message = "You're showing signs of fatigue and frequent context switching. Take a short break before continuing."
            reason = "Fatigue score is elevated ($fatigue/100) and $switches context switches were detected under $risk risk."
            action = "Take a short 10-minute break before continuing."
            resConf = if (conf == "HIGH" || conf == "MEDIUM") "HIGH" else "MEDIUM"
        }
        // 3. High Fatigue / Screen Strain
        else if (fatigue >= 65 || fatigueLvl == "HIGH" || trigger in listOf("HIGH_FATIGUE_STRAIN", "EXCESSIVE_SCREEN_TIME", "SEVERE_COGNITIVE_BURNOUT")) {
            if (trigger == "EXCESSIVE_SCREEN_TIME") {
                message = "Extended screen time is depleting your cognitive endurance. Step away from $task for a screen break."
                reason = "Fatigue level is high ($fatigue/100) due to continuous screen strain."
                action = "Step away from all screens for a 15-minute physical reset."
            } else {
                message = "High fatigue detected during $task. Step away for a restorative break before resuming."
                reason = "Cognitive fatigue score ($fatigue/100) has reached the high threshold."
                action = "Take a 15-minute recovery break or walk before resuming active tasks."
            }
            resConf = "HIGH"
        }
        // 4. High Distraction / Context Switching
        else if (switches >= 6 || distraction >= 60 || trigger == "RAPID_CONTEXT_SWITCHING") {
            message = "Frequent context switching detected during $task. Close secondary tabs and focus on one milestone."
            reason = "Elevated distraction with $switches context switches disrupting sustained attention."
            action = "Mute non-essential notifications and start a 25-minute single-task sprint."
            resConf = "HIGH"
        }
        // 5. Suboptimal Context / Off-Peak Friction / High Risk
        else if (trigger in listOf("VULNERABLE_TASK_CONTEXT", "OFF_PEAK_FRICTION", "PRODUCTIVITY_DROP") || risk == "HIGH") {
            if (trigger == "VULNERABLE_TASK_CONTEXT") {
                message = "Working on $task in $ctx shows high friction. Relocate to your best focus environment or shift to planning."
                reason = "Historical completion for $task is significantly lower in $ctx."
                action = "Relocate this session or shift to structured planning work."
            } else if (!isPeak && peak !in listOf("Insufficient Data", "None detected")) {
                message = "Working outside your peak window. Cap this $task block at 25 minutes and reschedule deep work to $peak."
                reason = "Timing is outside your calibrated peak window ($peak) with elevated task friction."
                action = "Cap current session at 25 minutes and schedule demanding blocks for $peak."
            } else {
                message = "Readiness for $task is at risk. Take a short breather and simplify your immediate task goal."
                reason = "Composite focus readiness ($score/100) indicates elevated friction in $ctx."
                action = "Take a 5-minute breather before starting a focused sprint."
            }
            resConf = if (conf == "LOW") "MEDIUM" else "HIGH"
        }
        // 6. Optimal Flow State
        else if (score >= 80 && fatigue < 35 && switches <= 2 && risk != "HIGH") {
            message = "Optimal focus state achieved for $task. Maintain your sustained momentum."
            reason = "High productivity readiness ($score/100) with low fatigue and minimal interruptions in $ctx."
            action = "Protect this focus block and continue uninterrupted in $ctx."
            resConf = "HIGH"
        }
        // 7. Normal Pacing (Default Steady State)
        else {
            message = "Pacing is steady for $task. Keep working through your current milestone."
            reason = "Balanced productivity readiness ($score/100) with manageable fatigue levels."
            action = "Continue your current task block with planned regular intervals."
            resConf = if (conf == "LOW") "MEDIUM" else "HIGH"
        }

        val elapsed = (System.currentTimeMillis() - startTime).toDouble()
        return AIModelResponse(
            message = message,
            reason = reason,
            action = action,
            confidence = resConf,
            provider = modelName,
            isFallback = true,
            latencyMs = elapsed
        )
    }
}

/**
 * Token-efficient prompt and response formatter for small language models.
 */
object PromptFormatter {
    const val SYSTEM_INSTRUCTION =
        "You are an on-device personal productivity coach running locally on an iQOO smartphone.\n" +
        "Analyze the provided behavioral telemetry evidence and output exactly one JSON object with natural-language coaching.\n" +
        "Rules:\n" +
        "1. Never output personal data, names, or URLs.\n" +
        "2. Keep the message to 1-2 concise, supportive, actionable sentences.\n" +
        "3. Output strictly valid JSON with keys: 'message', 'reason', 'action', 'confidence' (LOW, MEDIUM, HIGH).\n" +
        "4. No conversational filler or markdown formatting outside the JSON."

    fun formatPrompt(evidence: AIModelInput, template: String = "gemma"): String {
        val factsStr = if (evidence.facts.isNotEmpty()) evidence.facts.take(3).joinToString("; ") else "No anomalous flags"
        val evidenceBlock = """
            Telemetry Evidence:
            - Current Task: ${evidence.currentTask}
            - Focus Score: ${evidence.productivityScore}/100
            - Cognitive Fatigue: ${evidence.fatigue}/100 (${evidence.fatigueLevel})
            - Context Switches: ${evidence.contextSwitches} (Distraction: ${evidence.distraction}/100)
            - Environment: ${evidence.context}
            - Peak Window: ${evidence.peakWindow} (In Peak: ${evidence.isInPeakWindow})
            - Predicted Readiness: ${evidence.prediction}/100 (Risk: ${evidence.riskLevel})
            - Calibration Confidence: ${evidence.confidence}
            - Primary Trigger: ${evidence.detectedTrigger ?: "None"}
            - Observations: $factsStr
        """.trimIndent()

        return when (template) {
            "gemma" -> "<start_of_turn>user\n$SYSTEM_INSTRUCTION\n\n$evidenceBlock\nRespond with JSON:\n<start_of_turn>model\n{\"message\": \""
            "tinyllama" -> "<|system|>\n$SYSTEM_INSTRUCTION</s>\n<|user|>\n$evidenceBlock</s>\n<|assistant|>\n{\"message\": \""
            else -> "=== SYSTEM ===\n$SYSTEM_INSTRUCTION\n\n=== EVIDENCE ===\n$evidenceBlock\n\n=== COACH OUTPUT (JSON) ===\n{\"message\": \""
        }
    }
}

/**
 * Base adapter for on-device Small Language Models.
 */
abstract class BaseOnDeviceSLM(
    override val modelName: String,
    val modelPath: String? = null,
    val template: String = "gemma"
) : LocalAIModel {
    override val isFallback: Boolean = false
    override val isReady: Boolean get() = modelPath != null && File(modelPath).exists()

    abstract fun executeInference(prompt: String): String

    protected fun parseSlmJson(raw: String, input: AIModelInput, latency: Double): AIModelResponse {
        val fallback = FallbackAIModel()
        return try {
            val jsonStr = if (raw.startsWith("{\"message\": \"")) raw else "{\"message\": \"$raw"
            val msg = extractJsonValue(jsonStr, "message") ?: throw IllegalArgumentException("Missing message")
            val reason = extractJsonValue(jsonStr, "reason") ?: "On-device model generated coaching advice."
            val action = extractJsonValue(jsonStr, "action") ?: throw IllegalArgumentException("Missing action")
            val conf = extractJsonValue(jsonStr, "confidence") ?: "HIGH"

            AIModelResponse(
                message = msg,
                reason = reason,
                action = action,
                confidence = conf.uppercase(),
                provider = modelName,
                isFallback = false,
                latencyMs = latency
            )
        } catch (e: Exception) {
            val fallbackResp = fallback.generateCoaching(input)
            fallbackResp.copy(provider = "$modelName (fallback: malformed SLM output)")
        }
    }

    private fun extractJsonValue(json: String, key: String): String? {
        val pattern = Regex("\"$key\"\\s*:\\s*\"([^\"]+)\"")
        return pattern.find(json)?.groupValues?.getOrNull(1)
    }
}

/**
 * Concrete Android on-device model runner using Google MediaPipe GenAI (LiteRT).
 * Loads and runs INT4 quantized models (gemma-2b-it-cpu-int4.bin) on the physical iQOO phone.
 */
open class MediaPipeSLMModel(
    private val context: Context? = null,
    override val modelName: String = "mediapipe-gemma-2b-local",
    modelPath: String? = "/data/local/tmp/gemma-2b-it-cpu-int4.bin",
    val minFreeRamMb: Long = 400L,
    val timeoutMs: Long = 10000L,
    template: String = "gemma"
) : BaseOnDeviceSLM(modelName, modelPath, template) {

    private var nativeEngineInstance: Any? = null
    private val fallback = FallbackAIModel()

    init {
        initializeNativeEngineIfAvailable()
    }

    private fun initializeNativeEngineIfAvailable() {
        if (!isReady || context == null) return

        try {
            // Dynamically load Google MediaPipe GenAI Tasks if present on Android classpath:
            // com.google.mediapipe.tasks.genai.llminference.LlmInference
            val llmClass = Class.forName("com.google.mediapipe.tasks.genai.llminference.LlmInference")
            val optionsBuilderClass = Class.forName("com.google.mediapipe.tasks.genai.llminference.LlmInference\$LlmInferenceOptions")
            val builderMethod = optionsBuilderClass.getMethod("builder")
            val builder = builderMethod.invoke(null)

            builder.javaClass.getMethod("setModelPath", String::class.java).invoke(builder, modelPath)
            builder.javaClass.getMethod("setMaxTokens", Int::class.javaPrimitiveType).invoke(builder, 128)
            val options = builder.javaClass.getMethod("build").invoke(builder)

            val createMethod = llmClass.getMethod("createFromOptions", Context::class.java, optionsBuilderClass)
            nativeEngineInstance = createMethod.invoke(null, context, options)
        } catch (e: ClassNotFoundException) {
            nativeEngineInstance = null // Running outside MediaPipe AAR packaging
        } catch (e: Exception) {
            nativeEngineInstance = null
        }
    }

    protected open fun getAvailableMemoryMb(): Long {
        return try {
            val file = File("/proc/meminfo")
            if (file.exists()) {
                val line = file.bufferedReader().useLines { lines ->
                    lines.firstOrNull { it.startsWith("MemAvailable:") }
                }
                if (line != null) {
                    val parts = line.split("\\s+".toRegex())
                    if (parts.size >= 2) parts[1].toLong() / 1024L else 1024L
                } else {
                    val rt = Runtime.getRuntime()
                    (rt.maxMemory() - (rt.totalMemory() - rt.freeMemory())) / (1024L * 1024L)
                }
            } else {
                val rt = Runtime.getRuntime()
                (rt.maxMemory() - (rt.totalMemory() - rt.freeMemory())) / (1024L * 1024L)
            }
        } catch (e: Exception) {
            1024L
        }
    }

    override fun executeInference(prompt: String): String {
        val engine = nativeEngineInstance
            ?: throw IllegalStateException("MediaPipe GenAI native runtime is not loaded on this host.")

        val generateMethod = engine.javaClass.getMethod("generateResponse", String::class.java)
        return generateMethod.invoke(engine, prompt) as String
    }

    override fun generateCoaching(input: AIModelInput): AIModelResponse {
        // 1. Check if model weights exist on device
        if (!isReady) {
            val resp = fallback.generateCoaching(input)
            return resp.copy(provider = "$modelName (fallback: weights not installed at $modelPath)")
        }

        // 2. Check memory sufficiency
        val freeMem = getAvailableMemoryMb()
        if (freeMem < minFreeRamMb) {
            val resp = fallback.generateCoaching(input)
            return resp.copy(provider = "$modelName (fallback: low RAM ${freeMem}MB < ${minFreeRamMb}MB)")
        }

        // 3. Check native engine availability
        if (nativeEngineInstance == null) {
            val resp = fallback.generateCoaching(input)
            return resp.copy(provider = "$modelName (fallback: native MediaPipe AAR unlinked)")
        }

        // 4. Attempt inference with timeout
        val prompt = PromptFormatter.formatPrompt(input, template)
        val startTime = System.currentTimeMillis()

        return try {
            val executor = Executors.newSingleThreadExecutor()
            val future = executor.submit(Callable { executeInference(prompt) })
            val rawOutput = future.get(timeoutMs, TimeUnit.MILLISECONDS)
            val elapsed = (System.currentTimeMillis() - startTime).toDouble()
            parseSlmJson(rawOutput, input, elapsed)
        } catch (e: TimeoutException) {
            val resp = fallback.generateCoaching(input)
            resp.copy(provider = "$modelName (fallback: inference timeout > ${timeoutMs}ms)")
        } catch (e: Exception) {
            val resp = fallback.generateCoaching(input)
            resp.copy(provider = "$modelName (fallback: ${e.message?.take(40) ?: "inference error"})")
        }
    }
}

/**
 * Factory for instantiating the LocalAIModel on Android.
 */
object LocalAIModelFactory {
    fun getModel(
        context: Context? = null,
        provider: String = "fallback",
        modelPath: String = "/data/local/tmp/gemma-2b-it-cpu-int4.bin",
        minFreeRamMb: Long = 400L
    ): LocalAIModel {
        if (provider.equals("mediapipe", ignoreCase = true) ||
            provider.equals("gemma", ignoreCase = true) ||
            provider.equals("ondevice", ignoreCase = true)
        ) {
            if (File(modelPath).exists()) {
                return MediaPipeSLMModel(
                    context = context,
                    modelName = "mediapipe-gemma-2b-local",
                    modelPath = modelPath,
                    minFreeRamMb = minFreeRamMb
                )
            }
        }
        return FallbackAIModel()
    }
}
