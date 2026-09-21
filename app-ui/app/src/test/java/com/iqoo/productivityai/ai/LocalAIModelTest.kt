package com.iqoo.productivityai.ai

import org.junit.Assert.*
import org.junit.Test
import java.io.File

/**
 * Android JVM Unit Tests for Local AI Model Integration Layer.
 *
 * Tests input sanitization, prompt formatting, 4-tier fallback degradation,
 * memory guards, and schema conformity.
 *
 * NOTE: Does NOT mock or fake successful on-device SLM inference.
 * Tests strictly verify fallback behavior, config resolution, and heuristic correctness.
 */
class LocalAIModelTest {

    @Test
    fun testAIModelInput_fromEvidence_sanitizesAndClamps() {
        val rawEvidence = mapOf(
            "taskType" to "unrecognized_task_with_private_info_99",
            "score" to 150, // Out of bounds
            "fatigue" to -20, // Out of bounds
            "fatigueLevel" to "HIGH",
            "distraction" to 75,
            "contextSwitches" to 8,
            "location" to "Cafe",
            "prediction" to 40,
            "confidence" to "HIGH",
            "facts" to listOf("User switched apps rapidly", "Night-time session")
        )

        val input = AIModelInput.fromEvidence(rawEvidence)

        assertEquals("general", input.currentTask) // Sanitized to allowed set
        assertEquals(100, input.productivityScore) // Clamped to 100
        assertEquals(0, input.fatigue) // Clamped to 0
        assertEquals("HIGH", input.fatigueLevel)
        assertEquals(75, input.distraction)
        assertEquals(8, input.contextSwitches)
        assertEquals("Cafe", input.context)
        assertEquals(40, input.prediction)
        assertEquals("HIGH", input.confidence)
        assertEquals(2, input.facts.size)
    }

    @Test
    fun testAIModelInput_fromEvidence_preservesValidTask() {
        val raw = mapOf("currentTask" to "coding", "productivityScore" to 85)
        val input = AIModelInput.fromEvidence(raw)
        assertEquals("coding", input.currentTask)
        assertEquals(85, input.productivityScore)
    }

    @Test
    fun testFallbackAIModel_fatigueAndContextSwitchExemplar() {
        val model = FallbackAIModel()
        val input = AIModelInput(
            currentTask = "coding",
            productivityScore = 42,
            fatigue = 78,
            fatigueLevel = "HIGH",
            distraction = 65,
            contextSwitches = 7,
            context = "Home Office",
            riskLevel = "HIGH",
            confidence = "HIGH"
        )

        val response = model.generateCoaching(input)

        assertTrue(response.isFallback)
        assertEquals("deterministic-fallback-v1", response.provider)
        assertTrue(response.message.contains("fatigue and frequent context switching"))
        assertTrue(response.action.contains("10-minute break"))
        assertEquals("HIGH", response.confidence)
        assertTrue(response.reason.contains("Fatigue score is elevated"))
    }

    @Test
    fun testFallbackAIModel_excessiveScreenTimeTrigger() {
        val model = FallbackAIModel()
        val input = AIModelInput(
            currentTask = "reading",
            fatigue = 70,
            fatigueLevel = "HIGH",
            detectedTrigger = "EXCESSIVE_SCREEN_TIME"
        )

        val response = model.generateCoaching(input)

        assertTrue(response.isFallback)
        assertTrue(response.message.contains("Extended screen time"))
        assertTrue(response.action.contains("15-minute physical reset"))
    }

    @Test
    fun testFallbackAIModel_rapidContextSwitchingTrigger() {
        val model = FallbackAIModel()
        val input = AIModelInput(
            currentTask = "planning",
            contextSwitches = 8,
            distraction = 65,
            detectedTrigger = "RAPID_CONTEXT_SWITCHING"
        )

        val response = model.generateCoaching(input)

        assertTrue(response.isFallback)
        assertTrue(response.message.contains("Frequent context switching"))
        assertTrue(response.action.contains("single-task sprint"))
    }

    @Test
    fun testFallbackAIModel_flowState() {
        val model = FallbackAIModel()
        val input = AIModelInput(
            currentTask = "coding",
            productivityScore = 90,
            fatigue = 20,
            distraction = 10,
            contextSwitches = 1,
            riskLevel = "LOW",
            confidence = "HIGH"
        )

        val response = model.generateCoaching(input)

        assertTrue(response.isFallback)
        assertTrue(response.message.contains("Optimal focus state"))
        assertTrue(response.action.contains("continue uninterrupted"))
        assertEquals("HIGH", response.confidence)
    }

    @Test
    fun testFallbackAIModel_insufficientDataColdStart() {
        val model = FallbackAIModel()
        val input = AIModelInput(
            currentTask = "general",
            productivityScore = 50,
            fatigue = 0,
            distraction = 0,
            contextSwitches = 0,
            confidence = "LOW",
            detectedTrigger = "INSUFFICIENT_DATA"
        )

        val response = model.generateCoaching(input)

        assertTrue(response.isFallback)
        assertTrue(response.message.contains("calibration in progress"))
        assertEquals("LOW", response.confidence)
    }

    @Test
    fun testPromptFormatter_gemmaTemplate() {
        val input = AIModelInput(
            currentTask = "coding",
            productivityScore = 72,
            fatigue = 30,
            fatigueLevel = "LOW"
        )

        val prompt = PromptFormatter.formatPrompt(input, template = "gemma")

        assertTrue(prompt.startsWith("<start_of_turn>user\n"))
        assertTrue(prompt.contains("Telemetry Evidence:"))
        assertTrue(prompt.contains("Current Task: coding"))
        assertTrue(prompt.contains("Focus Score: 72/100"))
        assertTrue(prompt.endsWith("<start_of_turn>model\n{\"message\": \""))
    }

    @Test
    fun testPromptFormatter_tinyllamaTemplate() {
        val input = AIModelInput(
            currentTask = "writing",
            productivityScore = 65,
            fatigue = 45
        )

        val prompt = PromptFormatter.formatPrompt(input, template = "tinyllama")

        assertTrue(prompt.startsWith("<|system|>\n"))
        assertTrue(prompt.contains("<|user|>\n"))
        assertTrue(prompt.endsWith("<|assistant|>\n{\"message\": \""))
    }

    @Test
    fun testMediaPipeSLMModel_fallbackWhenWeightsMissing() {
        val nonExistentPath = "/tmp/does_not_exist_${System.currentTimeMillis()}.bin"
        val model = MediaPipeSLMModel(
            context = null,
            modelName = "mediapipe-gemma-2b-local",
            modelPath = nonExistentPath
        )

        assertFalse("Model with non-existent path must report isReady=false", model.isReady)

        val input = AIModelInput(currentTask = "coding", productivityScore = 40, fatigue = 80)
        val response = model.generateCoaching(input)

        assertTrue(response.isFallback)
        assertTrue(response.provider.contains("fallback: weights not installed"))
        assertNotNull(response.message)
        assertNotNull(response.action)
    }

    @Test
    fun testMediaPipeSLMModel_fallbackWhenMemoryInsufficient() {
        // Create temporary dummy file to simulate model weights on disk
        val tempModelFile = File.createTempFile("test_model_", ".bin")
        tempModelFile.deleteOnExit()

        // Create a model instance that reports low memory (100 MB available vs 400 MB required)
        val lowMemModel = object : MediaPipeSLMModel(
            context = null,
            modelName = "mediapipe-gemma-2b-local",
            modelPath = tempModelFile.absolutePath,
            config = ModelConfig(minFreeRamMb = 400L)
        ) {
            override fun getAvailableMemoryMb(): Long = 100L
        }

        assertTrue(lowMemModel.isReady)

        val input = AIModelInput(currentTask = "coding", productivityScore = 60)
        val response = lowMemModel.generateCoaching(input)

        assertTrue(response.isFallback)
        assertTrue(response.provider.contains("fallback: low RAM 100MB < 400MB"))
    }

    @Test
    fun testModelConfig_resolveModelPath_respectsExplicitPath() {
        val tempFile = File.createTempFile("custom_model_", ".task")
        tempFile.deleteOnExit()

        val resolved = ModelConfig.resolveModelPath(
            context = null,
            preferredPath = tempFile.absolutePath
        )

        assertEquals(tempFile.absolutePath, resolved)
    }

    @Test
    fun testModelConfig_resolveModelPath_candidateFallback() {
        val tempFile = File.createTempFile("candidate_model_", ".bin")
        tempFile.deleteOnExit()

        val resolved = ModelConfig.resolveModelPath(
            context = null,
            preferredPath = "/non/existent/path.bin",
            candidatePaths = listOf("/another/fake/path.bin", tempFile.absolutePath)
        )

        assertEquals(tempFile.absolutePath, resolved)
    }

    @Test
    fun testLocalAIModelFactory_returnsFallbackWhenRequested() {
        val model = LocalAIModelFactory.getModel(provider = "fallback")
        assertTrue(model.isFallback)
        assertEquals("deterministic-fallback-v1", model.modelName)
    }

    @Test
    fun testLocalAIModelFactory_returnsConfiguredMediaPipeModel() {
        val model = LocalAIModelFactory.getModel(
            provider = "mediapipe",
            modelPath = "/path/to/custom_gemma.bin",
            config = ModelConfig(minFreeRamMb = 500L)
        )

        assertFalse(model.isFallback)
        assertEquals("mediapipe-gemma-2b-local", model.modelName)
    }
}
