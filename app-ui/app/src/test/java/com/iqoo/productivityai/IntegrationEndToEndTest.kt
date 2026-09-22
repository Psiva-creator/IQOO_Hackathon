package com.iqoo.productivityai

import com.iqoo.productivityai.ai.AIModelInput
import com.iqoo.productivityai.ai.AIModelResponse
import com.iqoo.productivityai.ai.BaseOnDeviceSLM
import com.iqoo.productivityai.ai.FallbackAIModel
import com.iqoo.productivityai.ai.LocalAIModel
import com.iqoo.productivityai.ai.LocalAIModelFactory
import com.iqoo.productivityai.ai.ModelConfig
import com.iqoo.productivityai.context.ContextCapture
import com.iqoo.productivityai.context.ContextSignal
import com.iqoo.productivityai.engine.InsightEngine
import com.iqoo.productivityai.engine.PrivacySanitizer
import com.iqoo.productivityai.engine.UserModel
import com.iqoo.productivityai.engine.updateUserModel
import org.junit.Assert.*
import org.junit.Test
import java.util.UUID

/**
 * End-to-End Integration Test Suite for the full iQOO Productivity AI product.
 *
 * Verifies the complete pipeline:
 * Phone/Device Signals (Member C)
 *   → Task & Context Telemetry
 *   → Insight Engine (Member B)
 *   → Privacy Sanitization (PII, GPS, URLs, UUIDs stripped)
 *   → Canonical AIModelInput (14 fields)
 *   → LocalAIModel Boundary (Terminal 2)
 *   → Real Local SLM or Deterministic Fallback
 *   → Coach Response
 *   → UI Representation (Member A)
 *   → User Action Outcome
 *   → Personalization Update (Closed Loop)
 */
class IntegrationEndToEndTest {

    // Helper to generate seed tasks for reproducible test scenarios
    private fun createSampleTasks(count: Int = 10, completionRate: Double = 0.8): List<Task> {
        val now = System.currentTimeMillis()
        val tasks = mutableListOf<Task>()
        for (i in 0 until count) {
            val isCompleted = i < (count * completionRate).toInt()
            tasks.add(
                Task(
                    id = UUID.randomUUID().toString(),
                    title = "Development Task $i",
                    type = if (i % 2 == 0) "coding" else "writing",
                    createdAt = now - ((count - i) * 3600000L),
                    completedAt = if (isCompleted) now - ((count - i) * 3600000L) + 2400000L else null,
                    duration = if (isCompleted) 2400L else 300L,
                    location = "Home Office",
                    priority = "high"
                )
            )
        }
        return tasks
    }

    @Test
    fun testEndToEnd_NormalProductiveState() {
        // 1. Phone signal: steady productive session
        val contextSignal = ContextSignal(
            timestamp = System.currentTimeMillis(),
            appCategory = "Productivity",
            location = "Home Office",
            screenOnDuration = 1800L
        )

        // 2. Tasks: good completion rate
        val tasks = createSampleTasks(count = 10, completionRate = 0.8)

        // 3. Insight Engine analysis
        val engine = InsightEngine(tasks, listOf(contextSignal))
        val coach = engine.evaluateCurrentState(
            currentTaskType = "coding",
            currentContext = contextSignal.location,
            screenDuration = contextSignal.screenOnDuration,
            model = FallbackAIModel()
        )

        // 4. Assertions: Normal/Optimal state with steady pacing
        assertTrue(coach.state in listOf("NORMAL", "OPTIMAL"))
        assertNotNull(coach.structuredEvidence["currentTask"])
        assertEquals("coding", coach.structuredEvidence["currentTask"])
        assertNotNull(coach.fallbackMessage)
        assertTrue(coach.fallbackMessage.contains("coding") || coach.fallbackMessage.contains("steady") || coach.fallbackMessage.contains("focus"))
    }

    @Test
    fun testEndToEnd_HighFatigueState() {
        // 1. Phone signal: excessive screen time (130 minutes continuous)
        val contextSignal = ContextSignal(
            timestamp = System.currentTimeMillis(),
            appCategory = "Productivity",
            location = "Home Office",
            screenOnDuration = 130L * 60L
        )

        val tasks = createSampleTasks(count = 10, completionRate = 0.5)

        // 2. Insight Engine analysis
        val engine = InsightEngine(tasks, listOf(contextSignal))
        val coach = engine.evaluateCurrentState(
            currentTaskType = "writing",
            currentContext = contextSignal.location,
            screenDuration = contextSignal.screenOnDuration,
            model = FallbackAIModel()
        )

        // 3. Assertions: High fatigue trigger detected
        val fatigueScore = coach.structuredEvidence["fatigue"] as Int
        assertTrue("Fatigue score should be elevated", fatigueScore >= 30)
        assertEquals("writing", coach.structuredEvidence["currentTask"])
        assertNotNull(coach.fallbackMessage)
        assertTrue(coach.fallbackMessage.contains("fatigue") || coach.fallbackMessage.contains("break") || coach.fallbackMessage.contains("screen"))
    }

    @Test
    fun testEndToEnd_RapidContextSwitching() {
        // 1. Phone signal: rapid switches across social / entertainment apps
        val signals = listOf(
            ContextSignal(appCategory = "Social", screenOnDuration = 300L),
            ContextSignal(appCategory = "Entertainment", screenOnDuration = 600L),
            ContextSignal(appCategory = "Communication", screenOnDuration = 900L),
            ContextSignal(appCategory = "Social", screenOnDuration = 1200L),
            ContextSignal(appCategory = "Entertainment", screenOnDuration = 1500L),
            ContextSignal(appCategory = "Social", screenOnDuration = 1800L),
            ContextSignal(appCategory = "Communication", screenOnDuration = 2100L)
        )

        val tasks = createSampleTasks(count = 8, completionRate = 0.5)
        val engine = InsightEngine(tasks, signals)

        val coach = engine.evaluateCurrentState(
            currentTaskType = "planning",
            currentContext = "Cafe",
            model = FallbackAIModel()
        )

        val switches = coach.structuredEvidence["contextSwitches"] as Int
        assertTrue("Context switches should be detected", switches >= 6)
        assertEquals("planning", coach.structuredEvidence["currentTask"])
        assertTrue(coach.fallbackMessage.contains("context switch") || coach.fallbackMessage.contains("notification") || coach.fallbackMessage.contains("tabs"))
    }

    @Test
    fun testEndToEnd_PeakFocusState() {
        // 1. High completion rate, low fatigue, zero interruptions
        val contextSignal = ContextSignal(
            appCategory = "Productivity",
            location = "Home Office",
            screenOnDuration = 600L
        )

        val tasks = createSampleTasks(count = 15, completionRate = 1.0)
        val engine = InsightEngine(tasks, listOf(contextSignal))

        val coach = engine.evaluateCurrentState(
            currentTaskType = "coding",
            currentContext = "Home Office",
            screenDuration = 600L,
            model = FallbackAIModel()
        )

        val score = coach.structuredEvidence["productivityScore"] as Int
        assertTrue(score >= 70)
        assertTrue(coach.state in listOf("OPTIMAL", "NORMAL"))
        assertEquals("HIGH", coach.confidence)
    }

    @Test
    fun testEndToEnd_ColdStartInsufficientData() {
        // 0 tasks recorded
        val engine = InsightEngine(emptyList())
        val insights = engine.analyze()

        assertEquals("Insufficient Data", insights.peakHour)
        assertEquals("Calibrating", insights.confidenceLevel)
        assertEquals(0, insights.productivityScore)
        assertTrue(insights.recommendation.contains("tracking") || insights.recommendation.contains("activate"))

        val coach = engine.evaluateCurrentState(
            currentTaskType = "general",
            model = FallbackAIModel()
        )
        assertEquals("LOW", coach.confidence)
    }

    @Test
    fun testEndToEnd_MissingModelGracefulFallback() {
        // When local model is missing or null, FallbackAIModel provides deterministic coaching
        val tasks = createSampleTasks(count = 10)
        val engine = InsightEngine(tasks)

        val coach = engine.evaluateCurrentState(
            currentTaskType = "coding",
            model = null // null provider
        )

        assertNotNull(coach.structuredEvidence)
        assertNotNull(coach.fallbackMessage)
        assertFalse(coach.fallbackMessage.isBlank())
    }

    @Test
    fun testEndToEnd_ModelFailureTimeoutResilience() {
        // Simulate a failing SLM model that throws an exception or times out
        val failingModel = object : LocalAIModel {
            override val modelName: String = "failing-slm-mock"
            override val isFallback: Boolean = false
            override fun generateCoaching(input: AIModelInput): AIModelResponse {
                throw RuntimeException("Simulated hardware accelerator crash / timeout")
            }
        }

        val tasks = createSampleTasks(count = 10, completionRate = 0.2)
        val engine = InsightEngine(tasks)

        // Evaluate state should not crash; it must recover using FallbackAIModel
        val coach = engine.evaluateCurrentState(
            currentTaskType = "coding",
            model = failingModel
        )

        assertNotNull(coach.intervention)
        assertTrue(coach.modelProvider?.contains("fallback") == true)
        assertTrue(coach.fallbackMessage.isNotBlank())
    }

    @Test
    fun testEndToEnd_PrivacySanitizationFirewall() {
        // Raw dirty task with PII, GPS, email, URL, phone number, UUID
        val dirtyTask = Task(
            id = "b8d80e8e-6701-4475-81ef-e7c6b997fa94",
            title = "Secret meeting with john.doe@example.com about https://internal.company.com/leak at +1-555-867-5309",
            type = "unauthorized_custom_task_category_with_private_data",
            location = "37.7749,-122.4194 Cafe",
            priority = "high"
        )

        val contextSignal = ContextSignal(
            appCategory = "Productivity",
            location = "37.7749,-122.4194 LatLongCafe",
            screenOnDuration = 600L
        )

        val engine = InsightEngine(listOf(dirtyTask), listOf(contextSignal))
        val coach = engine.evaluateCurrentState(
            currentTaskType = dirtyTask.type,
            currentContext = dirtyTask.location,
            model = FallbackAIModel()
        )

        val evidence = coach.structuredEvidence
        val taskType = evidence["currentTask"] as String
        val ctx = evidence["context"] as String

        // 1. Task type sanitized to generic allowed set
        assertEquals("general", taskType)

        // 2. GPS location sanitized
        assertFalse("No raw GPS should be present", ctx.contains("37.7749"))

        // 3. Facts in evidence must not contain email or URL
        val facts = coach.evidence
        for (f in facts) {
            assertFalse("No emails in evidence", f.contains("john.doe@example.com"))
            assertFalse("No URLs in evidence", f.contains("https://"))
            assertFalse("No phone numbers in evidence", f.contains("555-867-5309"))
        }
    }

    @Test
    fun testEndToEnd_ClosedPersonalizationLearningLoop() {
        // Initial state with 5 tasks
        val initialTasks = createSampleTasks(count = 5, completionRate = 0.6)
        val initialEngine = InsightEngine(initialTasks)
        val initialResult = initialEngine.analyze()

        var userModel = UserModel(
            productivityProfile = initialResult.productivityProfile,
            tasks = initialTasks
        )

        // User performs and completes a new task in Home Office
        val newTask = Task(
            title = "Implement Security Gateway",
            type = "coding",
            createdAt = System.currentTimeMillis() - 3600000L,
            completedAt = System.currentTimeMillis(),
            duration = 3600L,
            location = "Home Office"
        )

        val contextSignal = ContextSignal(
            appCategory = "Productivity",
            location = "Home Office",
            screenOnDuration = 3600L
        )

        // Close the loop: update model with actual outcome
        userModel = updateUserModel(
            previousModel = userModel,
            newTask = newTask,
            context = contextSignal,
            predictedScore = 80 // Model predicted 80; actual was 100 (COMPLETED)
        )

        assertEquals(6, userModel.taskCount)
        assertEquals(1, userModel.predictionCalibration.totalEvaluations)
        assertEquals(1, userModel.predictionCalibration.accuratePredictions)
        assertEquals("ACCURATE", userModel.predictionCalibration.lastPredictionOutcome)
        assertEquals("COMPLETED", userModel.predictionCalibration.lastActualOutcome)
    }

    @Test
    fun testEndToEnd_ContextCaptureIntegration() {
        val capture = ContextCapture(currentLocation = "Home Office")
        val signal = capture.captureCurrentSignal(overridePackage = "com.android.chrome")

        assertEquals("Productivity", signal.appCategory)
        assertEquals("Home Office", signal.location)
        assertTrue(signal.screenOnDuration >= 0L)

        val socialSignal = capture.captureCurrentSignal(overridePackage = "com.instagram.android")
        assertEquals("Social", socialSignal.appCategory)
    }
}
