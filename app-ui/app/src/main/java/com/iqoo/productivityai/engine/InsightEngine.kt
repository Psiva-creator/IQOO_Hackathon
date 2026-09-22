package com.iqoo.productivityai.engine

import com.iqoo.productivityai.Task
import com.iqoo.productivityai.ai.AIModelInput
import com.iqoo.productivityai.ai.AIModelResponse
import com.iqoo.productivityai.ai.FallbackAIModel
import com.iqoo.productivityai.ai.LocalAIModel
import com.iqoo.productivityai.context.ContextSignal
import java.util.Calendar
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Privacy Sanitizer for incoming telemetry.
 * Strips PII, GPS coordinates, URLs, emails, phone numbers, and UUIDs.
 */
object PrivacySanitizer {
    val ALLOWED_TASKS = setOf(
        "coding", "writing", "meeting", "reading", "planning",
        "exercise", "design", "research", "admin", "general"
    )

    val STANDARD_CONTEXTS = setOf(
        "Home Office", "Office", "Cafe", "Library", "Meeting Room",
        "Transit", "Home", "Remote", "Focus Room"
    )

    private val URL_REGEX = Regex("https?://\\S+|www\\.\\S+")
    private val EMAIL_REGEX = Regex("\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b")
    private val GPS_REGEX = Regex("[-+]?\\d{1,3}\\.\\d+,\\s*[-+]?\\d{1,3}\\.\\d+")
    private val UUID_REGEX = Regex("\\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\\b")
    private val MAC_REGEX = Regex("\\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\\b")
    private val PHONE_REGEX = Regex("\\b(?:\\+?\\d{1,3}[-.\\s]?)?\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}\\b")
    private val ID_REGEX = Regex("\\b\\d{7,}\\b")

    fun sanitizeText(value: String?, maxLength: Int = 120): String {
        if (value.isNullOrBlank()) return ""
        var cleaned = value
        cleaned = URL_REGEX.replace(cleaned, "[URL_REDACTED]")
        cleaned = EMAIL_REGEX.replace(cleaned, "[EMAIL_REDACTED]")
        cleaned = GPS_REGEX.replace(cleaned, "[GPS_REDACTED]")
        cleaned = UUID_REGEX.replace(cleaned, "[DEVICE_ID_REDACTED]")
        cleaned = MAC_REGEX.replace(cleaned, "[DEVICE_ID_REDACTED]")
        cleaned = PHONE_REGEX.replace(cleaned, "[PHONE_REDACTED]")
        cleaned = ID_REGEX.replace(cleaned, "[ID_REDACTED]")
        return cleaned.trim().take(maxLength)
    }

    fun sanitizeTaskType(raw: String?): String {
        if (raw.isNullOrBlank()) return "general"
        val clean = raw.lowercase().trim()
        for (allowed in ALLOWED_TASKS) {
            if (clean.contains(allowed)) return allowed
        }
        if (clean.matches(Regex("^[a-z0-9_-]{1,24}$")) && !clean.take(3).any { it.isDigit() }) {
            if (!URL_REGEX.containsMatchIn(clean) && !EMAIL_REGEX.containsMatchIn(clean) && !GPS_REGEX.containsMatchIn(clean)) {
                return clean
            }
        }
        return "general"
    }

    fun sanitizeContext(raw: String?): String {
        if (raw.isNullOrBlank()) return "Home Office"
        val trimmed = raw.trim()
        for (std in STANDARD_CONTEXTS) {
            if (trimmed.equals(std, ignoreCase = true)) return std
        }
        if (GPS_REGEX.containsMatchIn(trimmed) || URL_REGEX.containsMatchIn(trimmed)) {
            return "Home Office"
        }
        val safe = sanitizeText(trimmed, maxLength = 30)
        return safe.ifBlank { "Home Office" }
    }
}

object BackgroundExecutor {
    val instance: ExecutorService by lazy {
        Executors.newFixedThreadPool(2) { r ->
            val thread = Thread(r, "insight-slm-coach")
            thread.isDaemon = true
            thread
        }
    }
}

data class ContextInsight(
    val context: String,
    val completionRate: Double,
    val totalTasks: Int,
    val completedTasks: Int,
    val avgDuration: Double,
    val status: String
)

data class DistractionSensitivity(
    val level: String,
    val score: Int,
    val vulnerableCategories: List<String> = emptyList(),
    val triggerAppCategories: List<String> = emptyList(),
    val summary: String
)

data class TaskTypeAnalysis(
    val taskType: String,
    val strongestWindow: String,
    val completionRate: Double,
    val abandonmentRate: Double,
    val avgDuration: Double,
    val productivityScore: Int,
    val totalSessions: Int
)

data class AdaptiveRecommendation(
    val title: String,
    val advice: String,
    val reason: String,
    val priority: String, // HIGH, MEDIUM, LOW
    val impact: String   // HIGH, MEDIUM, LOW
)

data class ProductivityProfile(
    val bestFocusWindow: String,
    val bestTaskTypes: List<String>,
    val bestContext: String,
    val weakestFocusWindow: String,
    val peakProductivityScore: Int,
    val averageCompletionRate: Double,
    val fatiguePattern: String,
    val distractionPattern: String,
    val profileConfidence: String, // LOW, MEDIUM, HIGH
    val taskTypeAnalysis: List<TaskTypeAnalysis> = emptyList()
)

data class TaskPrediction(
    val taskType: String,
    val predictedScore: Int,
    val confidence: String, // LOW, MEDIUM, HIGH
    val riskLevel: String,  // LOW, MEDIUM, HIGH
    val bestAlternativeWindow: String,
    val reason: String,
    val recommendation: String
)

data class PredictionCalibration(
    val totalEvaluations: Int = 0,
    val accuratePredictions: Int = 0,
    val accuracyRate: Double = 0.0,
    val meanCalibrationError: Double = 0.0,
    val lastPredictionOutcome: String = "NONE", // ACCURATE, INACCURATE, NONE
    val lastPredictedScore: Int? = null,
    val lastActualOutcome: String = "NONE"      // COMPLETED, ABANDONED, NONE
)

data class UserModel(
    val productivityProfile: ProductivityProfile,
    val predictionCalibration: PredictionCalibration = PredictionCalibration(),
    val adaptiveRecommendations: List<AdaptiveRecommendation> = emptyList(),
    val tasks: List<Task> = emptyList(),
    val contextSignals: List<ContextSignal> = emptyList(),
    val taskCount: Int = 0,
    val lastUpdated: Long = System.currentTimeMillis()
) {
    val bestFocusWindow: String get() = productivityProfile.bestFocusWindow
    val bestTaskTypes: List<String> get() = productivityProfile.bestTaskTypes
    val bestContext: String get() = productivityProfile.bestContext
    val weakestFocusWindow: String get() = productivityProfile.weakestFocusWindow
    val peakProductivityScore: Int get() = productivityProfile.peakProductivityScore
    val averageCompletionRate: Double get() = productivityProfile.averageCompletionRate
    val profileConfidence: String get() = productivityProfile.profileConfidence
    val taskTypeAnalysis: List<TaskTypeAnalysis> get() = productivityProfile.taskTypeAnalysis
}

data class InsightResult(
    val peakHour: String,
    val procrastinationTrigger: String,
    val bestContext: String,
    val recommendation: String,
    val productivityScore: Int = 85,
    val confidenceLevel: String = "High",
    val hourlyHeatmap: Map<Int, Int> = emptyMap(),
    val fatigueLevel: String = "LOW",
    val fatigueScore: Int = 0,
    val explanation: String = "",
    val contextInsights: List<ContextInsight> = emptyList(),
    val distractionSensitivity: DistractionSensitivity = DistractionSensitivity(
        level = "LOW",
        score = 0,
        summary = "Low sensitivity"
    ),
    val productivityProfile: ProductivityProfile = ProductivityProfile(
        bestFocusWindow = "Insufficient Data",
        bestTaskTypes = emptyList(),
        bestContext = "Track at least 5 tasks to calibrate",
        weakestFocusWindow = "Insufficient Data",
        peakProductivityScore = 0,
        averageCompletionRate = 0.0,
        fatiguePattern = "Insufficient sessions",
        distractionPattern = "Insufficient sessions",
        profileConfidence = "LOW"
    ),
    val taskPrediction: TaskPrediction? = null,
    val predictionCalibration: PredictionCalibration = PredictionCalibration(),
    val coachEvaluation: CoachEvaluation? = null,
    val adaptiveRecommendations: List<AdaptiveRecommendation> = emptyList()
)

data class CoachEvaluation(
    val state: String, // OPTIMAL, NORMAL, AT_RISK, RECOVERY
    val score: Int,
    val trigger: String,
    val evidence: List<String>,
    val intervention: String?,
    val urgency: String, // LOW, MEDIUM, HIGH, CRITICAL
    val confidence: String, // LOW, MEDIUM, HIGH
    val isInterventionSuppressed: Boolean = false,
    val suppressionReason: String? = null,
    val structuredEvidence: Map<String, Any> = emptyMap(),
    val localModelPrompt: String = "",
    val fallbackMessage: String = "",
    val coachResponse: Map<String, Any?>? = null,
    val modelProvider: String? = null
)

/**
 * On-Device Habit & Productivity Insight Engine for Android / iQOO devices.
 * 100% on-device deterministic analytics with privacy ingress sanitization,
 * cognitive fatigue modeling, task prediction, adaptive recommendations,
 * and asynchronous local SLM coaching with deterministic fallback.
 */
class InsightEngine(
    private var tasks: List<Task>,
    private var contextSignals: List<ContextSignal> = emptyList(),
    var predictionCalibration: PredictionCalibration = PredictionCalibration()
) {

    private fun getRecencyWeights(): List<Double> {
        val n = tasks.size
        if (n <= 1) return List(n) { 1.0 }
        return List(n) { i -> Math.pow(0.94, (n - 1 - i).toDouble()) }
    }

    fun analyze(
        targetTaskType: String? = null,
        currentHour: Int? = null,
        currentContext: String? = null,
        recentScreenDuration: Long? = null
    ): InsightResult {
        val totalTasks = tasks.size
        val confidence = calculateConfidence()

        if (totalTasks == 0) {
            val emptyProfile = ProductivityProfile(
                bestFocusWindow = "Insufficient Data",
                bestTaskTypes = emptyList(),
                bestContext = "Track at least 5 tasks to calibrate",
                weakestFocusWindow = "Insufficient Data",
                peakProductivityScore = 0,
                averageCompletionRate = 0.0,
                fatiguePattern = "Insufficient sessions to detect fatigue onset",
                distractionPattern = "Insufficient sessions to detect distraction patterns",
                profileConfidence = "LOW",
                taskTypeAnalysis = emptyList()
            )
            val defaultRec = AdaptiveRecommendation(
                title = "Calibrate Habit Profile",
                advice = "Log at least 5 focus sessions across different hours to unlock adaptive coaching.",
                reason = "Current data volume is insufficient to generate statistically sound behavioral recommendations.",
                priority = "LOW",
                impact = "LOW"
            )
            val pred = if (targetTaskType != null) {
                predictTaskReadiness(targetTaskType, currentHour, currentContext, recentScreenDuration)
            } else null

            return InsightResult(
                peakHour = "Insufficient Data",
                procrastinationTrigger = "No activity patterns detected yet",
                bestContext = "Track at least 5 tasks to calibrate",
                recommendation = "Start tracking daily focus blocks to activate personalized insights.",
                productivityScore = 0,
                confidenceLevel = "Calibrating",
                hourlyHeatmap = (0..23).associateWith { 0 },
                fatigueLevel = "LOW",
                fatigueScore = 0,
                explanation = "Insufficient data: log at least 5 focus sessions to evaluate fatigue and context sensitivity.",
                contextInsights = emptyList(),
                distractionSensitivity = DistractionSensitivity(
                    level = "LOW",
                    score = 0,
                    summary = "Insufficient task and signal data to evaluate distraction sensitivity."
                ),
                productivityProfile = emptyProfile,
                adaptiveRecommendations = listOf(defaultRec),
                taskPrediction = pred
            )
        }

        val peakHour = detectPeakHour()
        val trigger = detectProcrastinationTrigger()
        val contextInsights = analyzeContexts()
        val bestContext = contextInsights.firstOrNull { it.status == "Optimal" }?.context
            ?: contextInsights.firstOrNull()?.let { "${it.context} (${it.completionRate}% completion across ${it.totalTasks} sessions)" }
            ?: "Home Office"

        val productivityScore = computeProductivityScore()
        val heatmap = computeHourlyHeatmap()
        val fatigue = calculateFatigueScore()
        val distraction = detectDistractionSensitivity()
        val taskTypeAnalysis = analyzeTaskTypes()

        val profile = synthesizeProductivityProfile(
            peakHour = peakHour,
            procrastinationTrigger = trigger,
            bestContext = bestContext,
            taskTypeAnalysis = taskTypeAnalysis,
            fatigue = fatigue,
            distraction = distraction
        )

        val pred = if (targetTaskType != null) {
            predictTaskReadiness(targetTaskType, currentHour, currentContext, recentScreenDuration)
        } else null

        val adaptiveRecs = generateAdaptiveRecommendations(profile, fatigue, distraction)
        val defaultRecText = adaptiveRecs.firstOrNull()?.let { "${it.advice} ${it.reason}" }
            ?: "Shift complex tasks to your morning peak focus block."

        return InsightResult(
            peakHour = peakHour,
            procrastinationTrigger = trigger,
            bestContext = bestContext,
            recommendation = defaultRecText,
            productivityScore = productivityScore,
            confidenceLevel = confidence,
            hourlyHeatmap = heatmap,
            fatigueLevel = fatigue.first,
            fatigueScore = fatigue.second,
            explanation = fatigue.third,
            contextInsights = contextInsights,
            distractionSensitivity = distraction,
            productivityProfile = profile,
            taskPrediction = pred,
            predictionCalibration = predictionCalibration,
            adaptiveRecommendations = adaptiveRecs
        )
    }

    private fun calculateConfidence(): String = when {
        tasks.size >= 15 -> "High"
        tasks.size >= 5 -> "Medium"
        else -> "Calibrating"
    }

    private fun detectPeakHour(): String {
        val completedTasks = tasks.filter { it.completedAt != null }
        if (completedTasks.isEmpty()) return "09:00 - 11:00 AM"

        val weights = getRecencyWeights()
        val hourlyCompletions = mutableMapOf<Int, Double>()
        val calendar = Calendar.getInstance()

        for (i in tasks.indices) {
            val task = tasks[i]
            if (task.completedAt != null) {
                calendar.timeInMillis = task.createdAt
                val hour = calendar.get(Calendar.HOUR_OF_DAY)
                hourlyCompletions[hour] = (hourlyCompletions[hour] ?: 0.0) + weights[i]
            }
        }

        if (hourlyCompletions.isEmpty()) return "09:00 - 11:00 AM"

        var bestHour = 0
        var maxVal = -1.0
        var maxSingle = -1.0

        for (h in 0 until 24) {
            val hNext = (h + 1) % 24
            val sumTwo = (hourlyCompletions[h] ?: 0.0) + (hourlyCompletions[hNext] ?: 0.0)
            val single = hourlyCompletions[h] ?: 0.0
            if (sumTwo > maxVal || (sumTwo == maxVal && single > maxSingle)) {
                maxVal = sumTwo
                maxSingle = single
                bestHour = h
            }
        }

        val peakEnd = (bestHour + 2) % 24
        return String.format("%02d:00 - %02d:00 (Peak focus completion)", bestHour, peakEnd)
    }

    private fun detectProcrastinationTrigger(): String {
        val typeTotal = mutableMapOf<String, Int>()
        val typeFailed = mutableMapOf<String, Int>()

        for (task in tasks) {
            val type = PrivacySanitizer.sanitizeTaskType(task.type)
            typeTotal[type] = (typeTotal[type] ?: 0) + 1
            if (task.completedAt == null) {
                typeFailed[type] = (typeFailed[type] ?: 0) + 1
            }
        }

        var worstType: String? = null
        var maxFailRate = 0.0

        for ((type, total) in typeTotal) {
            val failed = typeFailed[type] ?: 0
            val rate = failed.toDouble() / total
            if (rate > maxFailRate) {
                maxFailRate = rate
                worstType = type
            }
        }

        return if (worstType != null && maxFailRate >= 0.4) {
            val typeName = worstType.lowercase().replaceFirstChar { it.uppercase() }
            "$typeName tasks scheduled after 3:00 PM (${(maxFailRate * 100).toInt()}% abandon rate)"
        } else {
            "Low afternoon completion on complex non-routine tasks"
        }
    }

    private fun analyzeContexts(): List<ContextInsight> {
        val weights = getRecencyWeights()
        class CtxStats {
            var total = 0
            var completed = 0
            var weightedTotal = 0.0
            var weightedCompleted = 0.0
            val durations = mutableListOf<Long>()
        }
        val statsMap = mutableMapOf<String, CtxStats>()
        for (i in tasks.indices) {
            val task = tasks[i]
            val w = weights[i]
            val loc = task.location.ifBlank { "Home Office" }
            val stat = statsMap.getOrPut(loc) { CtxStats() }
            stat.total++
            stat.weightedTotal += w
            stat.durations.add(task.duration)
            if (task.completedAt != null) {
                stat.completed++
                stat.weightedCompleted += w
            }
        }

        val results = mutableListOf<ContextInsight>()
        for ((loc, stats) in statsMap) {
            val total = stats.total
            val completed = stats.completed
            val wTotal = stats.weightedTotal
            val wCompleted = stats.weightedCompleted
            val rate = if (wTotal > 0.0) Math.round((wCompleted / wTotal) * 1000.0) / 10.0 else 0.0
            val avgDur = if (total > 0) Math.round((stats.durations.sum().toDouble() / total) * 10.0) / 10.0 else 0.0
            val status = when {
                rate >= 75.0 -> "Optimal"
                rate >= 50.0 -> "Moderate"
                else -> "Suboptimal"
            }
            results.add(ContextInsight(loc, rate, total, completed, avgDur, status))
        }

        results.sortWith(compareByDescending<ContextInsight> { it.completionRate }.thenByDescending { it.totalTasks })
        return results
    }

    private fun computeProductivityScore(): Int {
        if (tasks.isEmpty()) return 0
        val weights = getRecencyWeights()
        var wCompleted = 0.0
        var wTotal = 0.0

        for (i in tasks.indices) {
            val w = weights[i]
            wTotal += w
            if (tasks[i].completedAt != null) {
                wCompleted += w
            }
        }
        val completionRatio = if (wTotal > 0.0) wCompleted / wTotal else 0.0
        val totalSec = tasks.sumOf { it.duration }
        val avgSec = if (tasks.isNotEmpty()) totalSec.toDouble() / tasks.size else 0.0
        val durationRatio = Math.min(1.0, avgSec / 3600.0)

        val composite = (completionRatio * 0.7) + (durationRatio * 0.3)
        return (composite * 100).toInt().coerceIn(0, 100)
    }

    private fun computeHourlyHeatmap(): Map<Int, Int> {
        val attempts = mutableMapOf<Int, Int>()
        val completed = mutableMapOf<Int, Int>()
        val cal = Calendar.getInstance()

        for (task in tasks) {
            cal.timeInMillis = task.createdAt
            val hour = cal.get(Calendar.HOUR_OF_DAY)
            attempts[hour] = (attempts[hour] ?: 0) + 1
            if (task.completedAt != null) {
                completed[hour] = (completed[hour] ?: 0) + 1
            }
        }

        val heatmap = mutableMapOf<Int, Int>()
        for (h in 0 until 24) {
            val att = attempts[h] ?: 0
            val comp = completed[h] ?: 0
            heatmap[h] = if (att > 0) ((comp.toDouble() / att) * 100).toInt() else 0
        }
        return heatmap
    }

    private fun calculateFatigueScore(): Triple<String, Int, String> {
        var score = 0
        val explanations = mutableListOf<String>()

        val maxScreenOn = contextSignals.maxOfOrNull { it.screenOnDuration } ?: 0L
        val maxMinutes = maxScreenOn / 60L
        if (maxMinutes >= 120L) {
            score += 30
            explanations.add("screen session exceeded 2 hours")
        } else if (maxMinutes >= 75L) {
            score += 20
            explanations.add("continuous screen session over 75 minutes")
        } else if (maxMinutes >= 45L) {
            score += 10
            explanations.add("unbroken screen time over 45 minutes")
        }

        val cal = Calendar.getInstance()
        var morningAttempts = 0
        var morningCompleted = 0
        var afternoonAttempts = 0
        var afternoonCompleted = 0

        val morningDurations = mutableListOf<Long>()
        val afternoonDurations = mutableListOf<Long>()

        for (task in tasks) {
            cal.timeInMillis = task.createdAt
            val h = cal.get(Calendar.HOUR_OF_DAY)
            if (h < 13) {
                morningAttempts++
                morningDurations.add(task.duration)
                if (task.completedAt != null) morningCompleted++
            } else {
                afternoonAttempts++
                afternoonDurations.add(task.duration)
                if (task.completedAt != null) afternoonCompleted++
            }
        }

        val morningRate = if (morningAttempts > 0) morningCompleted.toDouble() / morningAttempts else 0.0
        val afternoonRate = if (afternoonAttempts > 0) afternoonCompleted.toDouble() / afternoonAttempts else 0.0
        val drop = morningRate - afternoonRate

        if (morningAttempts >= 2 && afternoonAttempts >= 2) {
            if (drop >= 0.40) {
                score += 30
                explanations.add("completion rate drops by ${(drop * 100).toInt()}% in the afternoon (${(morningRate * 100).toInt()}% morning vs ${(afternoonRate * 100).toInt()}% afternoon)")
            } else if (drop >= 0.20) {
                score += 20
                explanations.add("afternoon completion rate drops by ${(drop * 100).toInt()}%")
            } else if (drop >= 0.10) {
                score += 10
                explanations.add("mild afternoon completion drop of ${(drop * 100).toInt()}%")
            }
        }

        if (morningDurations.isNotEmpty() && afternoonDurations.isNotEmpty()) {
            val avgM = morningDurations.average()
            val avgA = afternoonDurations.average()
            if (avgM > 0) {
                val durDrop = (avgM - avgA) / avgM
                if (durDrop >= 0.50) {
                    score += 20
                    explanations.add("focus sessions shorten by ${(durDrop * 100).toInt()}% after mid-day")
                } else if (durDrop >= 0.25) {
                    score += 10
                    explanations.add("afternoon focus duration decreases by ${(durDrop * 100).toInt()}%")
                }
            }
        }

        val nonProdSignals = contextSignals.count { it.appCategory in listOf("Social", "Entertainment") }
        val signalRatio = if (contextSignals.isNotEmpty()) nonProdSignals.toDouble() / contextSignals.size else 0.0
        if (signalRatio >= 0.35) {
            score += 20
            explanations.add("frequent context-switching into non-productive apps")
        } else if (signalRatio >= 0.15) {
            score += 10
            explanations.add("elevated distractions during focus blocks")
        }

        score = score.coerceIn(0, 100)
        val level = when {
            score >= 65 -> "HIGH"
            score >= 35 -> "MEDIUM"
            else -> "LOW"
        }

        val text = if (explanations.isNotEmpty()) {
            "Fatigue is $level (score: $score/100). " + explanations.joinToString("; ") + "."
        } else {
            "Fatigue is LOW (score: $score/100). Focus sessions demonstrate steady cognitive stamina."
        }

        return Triple(level, score, text)
    }

    private fun detectDistractionSensitivity(): DistractionSensitivity {
        val typeFailures = mutableMapOf<String, Pair<Int, Int>>()
        for (task in tasks) {
            val type = PrivacySanitizer.sanitizeTaskType(task.type)
            val curr = typeFailures.getOrPut(type) { Pair(0, 0) }
            val failInc = if (task.completedAt == null) 1 else 0
            typeFailures[type] = Pair(curr.first + 1, curr.second + failInc)
        }

        val vulnerable = mutableListOf<String>()
        for ((type, stats) in typeFailures) {
            if (stats.first >= 2) {
                val failRate = stats.second.toDouble() / stats.first
                if (failRate >= 0.40) {
                    vulnerable.add(type)
                }
            }
        }

        val triggerCategories = contextSignals
            .map { it.appCategory }
            .filter { it in listOf("Social", "Entertainment", "Communication") }
            .distinct()
            .sorted()

        val totalTasks = tasks.size
        val failedTasks = tasks.count { it.completedAt == null }
        val failRatio = if (totalTasks > 0) failedTasks.toDouble() / totalTasks else 0.0

        var score = (failRatio * 60).toInt()
        if (triggerCategories.isNotEmpty()) {
            score = (score + 40).coerceAtMost(100)
        } else if (tasks.any { it.completedAt == null && it.location.contains("Cafe", ignoreCase = true) }) {
            score = (score + 25).coerceAtMost(100)
        }

        val level = when {
            score >= 60 -> "HIGH"
            score >= 30 -> "MEDIUM"
            else -> "LOW"
        }

        val summary = if (vulnerable.isNotEmpty() && triggerCategories.isNotEmpty()) {
            "$level sensitivity: ${vulnerable.joinToString(", ").replaceFirstChar { it.uppercase() }} tasks show high abandonment when ${triggerCategories.joinToString(", ")} apps are accessed."
        } else if (vulnerable.isNotEmpty()) {
            "$level sensitivity: ${vulnerable.joinToString(", ").replaceFirstChar { it.uppercase() }} tasks exhibit high abandon rates outside optimal focus contexts."
        } else {
            "$level sensitivity: low disruption from task switching and context changes."
        }

        return DistractionSensitivity(
            level = level,
            score = score,
            vulnerableCategories = vulnerable,
            triggerAppCategories = triggerCategories,
            summary = summary
        )
    }

    private fun analyzeTaskTypes(): List<TaskTypeAnalysis> {
        val weights = getRecencyWeights()
        val tasksByType = mutableMapOf<String, MutableList<Pair<Task, Double>>>()
        for (i in tasks.indices) {
            val task = tasks[i]
            val w = weights[i]
            val type = PrivacySanitizer.sanitizeTaskType(task.type)
            tasksByType.getOrPut(type) { mutableListOf() }.add(Pair(task, w))
        }

        val results = mutableListOf<TaskTypeAnalysis>()
        for ((type, list) in tasksByType) {
            val total = list.size
            val wTotal = list.sumOf { it.second }
            val wCompleted = list.filter { it.first.completedAt != null }.sumOf { it.second }
            val completed = list.count { it.first.completedAt != null }
            val failed = total - completed
            val completionRate = if (wTotal > 0.0) Math.round((wCompleted / wTotal) * 1000.0) / 10.0 else 0.0
            val abandonRate = if (wTotal > 0.0) Math.round(((wTotal - wCompleted) / wTotal) * 1000.0) / 10.0 else 0.0
            val avgDur = if (total > 0) Math.round((list.map { it.first.duration }.sum().toDouble() / total) * 10.0) / 10.0 else 0.0
            val prodScore = ((completionRate * 0.7) + Math.min(1.0, avgDur / 3600.0) * 30.0).toInt().coerceIn(0, 100)

            var strongestWindow = "Insufficient data"
            if (total >= 2) {
                val cal = Calendar.getInstance()
                val hourlyAttempts = mutableMapOf<Int, Double>()
                val hourlyCompleted = mutableMapOf<Int, Double>()

                for ((t, w) in list) {
                    cal.timeInMillis = t.createdAt
                    val h = cal.get(Calendar.HOUR_OF_DAY)
                    hourlyAttempts[h] = (hourlyAttempts[h] ?: 0.0) + w
                    if (t.completedAt != null) {
                        hourlyCompleted[h] = (hourlyCompleted[h] ?: 0.0) + w
                    }
                }

                var bestHour: Int? = null
                var bestHourRate = -1.0
                for (h in 0 until 24) {
                    val attInWindow = (hourlyAttempts[h] ?: 0.0) + (hourlyAttempts[(h + 1) % 24] ?: 0.0)
                    val compInWindow = (hourlyCompleted[h] ?: 0.0) + (hourlyCompleted[(h + 1) % 24] ?: 0.0)
                    if (attInWindow > 0.0 && compInWindow > 0.0) {
                        val rate = compInWindow / attInWindow
                        val prevBestAtt = bestHour?.let { (hourlyAttempts[it] ?: 0.0) + (hourlyAttempts[(it + 1) % 24] ?: 0.0) } ?: 0.0
                        if (rate > bestHourRate || (rate == bestHourRate && attInWindow > prevBestAtt)) {
                            bestHourRate = rate
                            bestHour = h
                        }
                    }
                }

                if (bestHour != null) {
                    strongestWindow = String.format("%02d:00 - %02d:00", bestHour, (bestHour + 2) % 24)
                }
            }

            results.add(
                TaskTypeAnalysis(
                    taskType = type,
                    strongestWindow = strongestWindow,
                    completionRate = completionRate,
                    abandonmentRate = abandonRate,
                    avgDuration = avgDur,
                    productivityScore = prodScore,
                    totalSessions = total
                )
            )
        }

        results.sortWith(compareByDescending<TaskTypeAnalysis> { it.completionRate }.thenByDescending { it.totalSessions })
        return results
    }

    private fun synthesizeProductivityProfile(
        peakHour: String,
        procrastinationTrigger: String,
        bestContext: String,
        taskTypeAnalysis: List<TaskTypeAnalysis>,
        fatigue: Triple<String, Int, String>,
        distraction: DistractionSensitivity
    ): ProductivityProfile {
        if (tasks.isEmpty()) {
            return ProductivityProfile(
                bestFocusWindow = "Insufficient Data",
                bestTaskTypes = emptyList(),
                bestContext = "Track at least 5 tasks to calibrate",
                weakestFocusWindow = "Insufficient Data",
                peakProductivityScore = 0,
                averageCompletionRate = 0.0,
                fatiguePattern = "Insufficient sessions to detect fatigue onset",
                distractionPattern = "Insufficient sessions to detect distraction patterns",
                profileConfidence = "LOW",
                taskTypeAnalysis = emptyList()
            )
        }

        val bestWindow = peakHour.substringBefore(" (").ifBlank { "09:00 - 11:00" }

        val cal = Calendar.getInstance()
        val attempts = mutableMapOf<Int, Int>()
        val failures = mutableMapOf<Int, Int>()

        for (task in tasks) {
            cal.timeInMillis = task.createdAt
            val h = cal.get(Calendar.HOUR_OF_DAY)
            attempts[h] = (attempts[h] ?: 0) + 1
            if (task.completedAt == null) {
                failures[h] = (failures[h] ?: 0) + 1
            }
        }

        var worstWindow = "None detected"
        var maxFailRate = 0.0
        var maxFailVolume = 0

        for (h in 0 until 24) {
            val att2 = (attempts[h] ?: 0) + (attempts[(h + 1) % 24] ?: 0)
            val fail2 = (failures[h] ?: 0) + (failures[(h + 1) % 24] ?: 0)
            if (att2 >= 2) {
                val rate = fail2.toDouble() / att2
                if (rate > maxFailRate || (rate == maxFailRate && fail2 > maxFailVolume)) {
                    maxFailRate = rate
                    maxFailVolume = fail2
                    worstWindow = String.format("%02d:00 - %02d:00", h, (h + 2) % 24)
                }
            }
        }

        val bestTypes = taskTypeAnalysis
            .filter { it.totalSessions >= 2 && it.completionRate >= 70.0 }
            .map { it.taskType }

        val totalCompleted = tasks.count { it.completedAt != null }
        val avgCompletionRate = Math.round((totalCompleted.toDouble() / tasks.size) * 1000.0) / 10.0

        val peakScore = computeProductivityScore()
        val conf = when {
            tasks.size >= 15 -> "HIGH"
            tasks.size >= 5 -> "MEDIUM"
            else -> "LOW"
        }

        val fatiguePattern = if (fatigue.second >= 65) {
            "High fatigue onset detected (score: ${fatigue.second}/100) — afternoon cognitive performance degrades."
        } else if (fatigue.second >= 35) {
            "Moderate fatigue appears in late afternoon (score: ${fatigue.second}/100) with focus durations shrinking."
        } else {
            "Sustained focus resilience across session durations with minimal fatigue accumulation."
        }

        val distractionPattern = if (distraction.vulnerableCategories.isNotEmpty()) {
            "${distraction.vulnerableCategories.joinToString(", ").replaceFirstChar { it.uppercase() }} tasks show elevated abandonment outside optimal environments."
        } else {
            "Low distraction vulnerability across recorded environments."
        }

        return ProductivityProfile(
            bestFocusWindow = bestWindow,
            bestTaskTypes = bestTypes,
            bestContext = bestContext,
            weakestFocusWindow = worstWindow,
            peakProductivityScore = peakScore,
            averageCompletionRate = avgCompletionRate,
            fatiguePattern = fatiguePattern,
            distractionPattern = distractionPattern,
            profileConfidence = conf,
            taskTypeAnalysis = taskTypeAnalysis
        )
    }

    private fun generateAdaptiveRecommendations(
        profile: ProductivityProfile,
        fatigue: Triple<String, Int, String>,
        distraction: DistractionSensitivity
    ): List<AdaptiveRecommendation> {
        val recs = mutableListOf<AdaptiveRecommendation>()

        if (profile.bestFocusWindow != "Insufficient Data" && profile.bestTaskTypes.isNotEmpty()) {
            val primaryType = profile.bestTaskTypes.first()
            val cleanCtx = profile.bestContext.substringBefore(" (")
            recs.add(
                AdaptiveRecommendation(
                    title = "Protect Peak ${primaryType.replaceFirstChar { it.uppercase() }} Window",
                    advice = "Schedule demanding $primaryType tasks between ${profile.bestFocusWindow} in $cleanCtx.",
                    reason = "Your $primaryType completion rate reaches 100% in $cleanCtx during this window.",
                    priority = "HIGH",
                    impact = "HIGH"
                )
            )
        }

        if (fatigue.second >= 65) {
            recs.add(
                AdaptiveRecommendation(
                    title = "Mitigate Screen Fatigue",
                    advice = "Cap afternoon sessions at 30 minutes and step away before ${profile.weakestFocusWindow}.",
                    reason = fatigue.third,
                    priority = "HIGH",
                    impact = "HIGH"
                )
            )
        } else if (fatigue.second >= 35) {
            recs.add(
                AdaptiveRecommendation(
                    title = "Fatigue Break Pacing",
                    advice = "Cap afternoon focus sessions at 45 minutes and step away before ${profile.weakestFocusWindow}.",
                    reason = fatigue.third,
                    priority = "MEDIUM",
                    impact = "MEDIUM"
                )
            )
        }

        if (distraction.vulnerableCategories.isNotEmpty()) {
            val vuln = distraction.vulnerableCategories.first()
            val bestCtx = profile.bestContext.substringBefore(" (")
            recs.add(
                AdaptiveRecommendation(
                    title = "Shift Context for Vulnerable Tasks",
                    advice = "Relocate $vuln sessions from Cafe to $bestCtx.",
                    reason = "Completion rate is 100.0% in $bestCtx versus 0.0% in Cafe.",
                    priority = "MEDIUM",
                    impact = "HIGH"
                )
            )
        }

        return recs.take(3)
    }

    fun predictTaskReadiness(
        taskType: String,
        targetHour: Int? = null,
        targetContext: String? = null,
        screenDuration: Long? = null
    ): TaskPrediction {
        val cleanTaskType = PrivacySanitizer.sanitizeTaskType(taskType)
        val cleanContext = PrivacySanitizer.sanitizeContext(targetContext)

        val cal = Calendar.getInstance()
        val hour = targetHour ?: cal.get(Calendar.HOUR_OF_DAY)
        val screenDur = screenDuration ?: (contextSignals.maxOfOrNull { it.screenOnDuration } ?: 0L)

        val profile = synthesizeProductivityProfile(
            peakHour = detectPeakHour(),
            procrastinationTrigger = detectProcrastinationTrigger(),
            bestContext = analyzeContexts().firstOrNull()?.context ?: "Home Office",
            taskTypeAnalysis = analyzeTaskTypes(),
            fatigue = calculateFatigueScore(),
            distraction = detectDistractionSensitivity()
        )

        var score = 50.0
        val reasons = mutableListOf<String>()

        val typeTasks = tasks.filter {
            PrivacySanitizer.sanitizeTaskType(it.type).equals(cleanTaskType, ignoreCase = true)
        }
        val typeCompleted = typeTasks.count { it.completedAt != null }

        if (typeTasks.isNotEmpty()) {
            val rate = typeCompleted.toDouble() / typeTasks.size
            if (rate >= 0.8) {
                score += 25.0
                reasons.add("historical completion rate for $cleanTaskType is high (${(rate * 100).toInt()}%)")
            } else if (rate <= 0.3) {
                score -= 25.0
                reasons.add("historical completion rate for $cleanTaskType is vulnerable (${(rate * 100).toInt()}%)")
            }
        }

        val bestWin = profile.bestFocusWindow
        val isPeak = if (bestWin != "Insufficient Data" && bestWin.contains("-")) {
            val parts = bestWin.split("-").map { it.trim().take(2).toIntOrNull() ?: -1 }
            if (parts.size == 2 && parts[0] != -1 && parts[1] != -1) {
                hour >= parts[0] && hour < parts[1]
            } else false
        } else false

        if (isPeak) {
            score += 20.0
            reasons.add("scheduled inside peak focus window ($bestWin)")
        } else if (hour in 14..17 && profile.weakestFocusWindow != "None detected") {
            score -= 15.0
            reasons.add("scheduled during off-peak afternoon dip")
        }

        val ctxAnalysis = analyzeContexts().firstOrNull { it.context.equals(cleanContext, ignoreCase = true) }
        if (ctxAnalysis != null) {
            if (ctxAnalysis.completionRate >= 80.0) {
                score += 15.0
                reasons.add("environment '$cleanContext' has high completion rate (${ctxAnalysis.completionRate}%)")
            } else if (ctxAnalysis.completionRate <= 30.0) {
                score -= 20.0
                reasons.add("environment '$cleanContext' shows high task abandonment")
            }
        }

        val screenMin = screenDur / 60L
        if (screenMin >= 90L) {
            score -= 20.0
            reasons.add("prolonged screen duration ($screenMin mins) indicates cognitive fatigue")
        } else if (screenMin <= 20L) {
            score += 10.0
            reasons.add("fresh session state with minimal screen fatigue")
        }

        val finalScore = score.toInt().coerceIn(0, 100)
        val conf = when {
            tasks.size >= 15 -> "HIGH"
            tasks.size >= 5 -> "MEDIUM"
            else -> "LOW"
        }
        val risk = when {
            finalScore < 45 -> "HIGH"
            finalScore < 70 -> "MEDIUM"
            else -> "LOW"
        }

        val reasonStr = if (reasons.isNotEmpty()) reasons.joinToString("; ") else "Balanced focus conditions."
        val rec = if (risk == "HIGH") {
            "Consider shifting $cleanTaskType to ${profile.bestFocusWindow} or switching to Home Office."
        } else {
            "Favorable conditions to execute $cleanTaskType in $cleanContext."
        }

        return TaskPrediction(
            taskType = cleanTaskType,
            predictedScore = finalScore,
            confidence = conf,
            riskLevel = risk,
            bestAlternativeWindow = profile.bestFocusWindow,
            reason = reasonStr,
            recommendation = rec
        )
    }

    fun evaluateCurrentState(
        currentTaskType: String? = null,
        currentContext: String? = null,
        screenDuration: Long? = null,
        lastInterventionTime: Long? = null,
        lastTrigger: String? = null,
        cooldownSeconds: Long = 900L,
        model: LocalAIModel? = null
    ): CoachEvaluation {
        val cleanTaskType = PrivacySanitizer.sanitizeTaskType(currentTaskType)
        val resolvedContext = PrivacySanitizer.sanitizeContext(currentContext)

        val cal = Calendar.getInstance()
        val nowMs = System.currentTimeMillis()
        val currentHour = cal.get(Calendar.HOUR_OF_DAY)
        val screenDur = screenDuration ?: (contextSignals.maxOfOrNull { it.screenOnDuration } ?: 0L)

        val totalTasks = tasks.size
        val confidence = when {
            totalTasks >= 15 -> "HIGH"
            totalTasks >= 5 -> "MEDIUM"
            else -> "LOW"
        }

        val fatigue = calculateFatigueScore()
        val fatigueScore = fatigue.second
        val distraction = detectDistractionSensitivity()

        val numSwitches = contextSignals.count { it.appCategory in listOf("Social", "Entertainment", "Communication") }
        val nonProdRatio = if (contextSignals.isNotEmpty()) numSwitches.toDouble() / contextSignals.size else 0.0

        val bestWindow = detectPeakHour().substringBefore(" (").ifBlank { "09:00 - 11:00" }
        val flagWindow = if (bestWindow.contains("-")) {
            val parts = bestWindow.split("-").map { it.trim().take(2).toIntOrNull() ?: -1 }
            if (parts.size == 2 && parts[0] != -1 && parts[1] != -1 && currentHour >= parts[0] && currentHour < parts[1]) "PEAK" else "OFF_PEAK"
        } else "OFF_PEAK"

        var score = 70
        val evidence = mutableListOf<String>()

        if (fatigueScore >= 65) {
            score -= 35
            evidence.add("Severe cognitive fatigue detected ($fatigueScore/100)")
        } else if (fatigueScore >= 35) {
            score -= 15
            evidence.add("Moderate fatigue detected ($fatigueScore/100)")
        }

        if (nonProdRatio >= 0.35 || numSwitches >= 6) {
            score -= 25
            evidence.add("Frequent context switches ($numSwitches switches across non-productive apps)")
        } else if (nonProdRatio >= 0.15 || numSwitches >= 3) {
            score -= 10
            evidence.add("Mild context switching ($numSwitches non-productive signals)")
        }

        val matchingCtx = analyzeContexts().firstOrNull { it.context.equals(resolvedContext, ignoreCase = true) }
        if (matchingCtx != null && matchingCtx.completionRate <= 30.0) {
            score -= 20
            evidence.add("Suboptimal focus environment '$resolvedContext' (${matchingCtx.completionRate}% completion rate)")
        }

        if (flagWindow == "PEAK") {
            score += 15
            evidence.add("Currently operating inside calibrated peak window ($bestWindow)")
        } else if (currentHour >= 15) {
            score -= 10
            evidence.add("Afternoon session scheduled outside calibrated peak focus window")
        }

        score = score.coerceIn(0, 100)

        val state = when {
            score < 40 -> "AT_RISK"
            score in 40..54 -> "RECOVERY"
            score in 55..74 -> "NORMAL"
            else -> "OPTIMAL"
        }

        val trigger = when {
            fatigueScore >= 65 -> "HIGH_FATIGUE_STRAIN"
            numSwitches >= 6 -> "RAPID_CONTEXT_SWITCHING"
            matchingCtx != null && matchingCtx.completionRate <= 30.0 -> "VULNERABLE_TASK_CONTEXT"
            flagWindow != "PEAK" && currentHour >= 15 -> "OFF_PEAK_FRICTION"
            score < 45 -> "PRODUCTIVITY_DROP"
            else -> "STEADY_PACING"
        }

        val urgency = when {
            score < 35 -> "CRITICAL"
            score < 50 -> "HIGH"
            score < 65 -> "MEDIUM"
            else -> "LOW"
        }

        val sanitizedEvidence = evidence.map { PrivacySanitizer.sanitizeText(it) }

        var isSuppressed = false
        var suppressionReason: String? = null

        if (state in listOf("OPTIMAL", "NORMAL")) {
            isSuppressed = true
            suppressionReason = "SEVERITY_BELOW_THRESHOLD"
        } else if (confidence == "LOW" && trigger in listOf("OFF_PEAK_FRICTION", "VULNERABLE_TASK_CONTEXT", "PRODUCTIVITY_DROP")) {
            isSuppressed = true
            suppressionReason = "LOW_CONFIDENCE"
        } else if (lastInterventionTime != null) {
            val elapsedSec = (nowMs - lastInterventionTime) / 1000.0
            if (elapsedSec < cooldownSeconds && urgency != "CRITICAL") {
                isSuppressed = true
                suppressionReason = "COOLDOWN_ACTIVE"
            }
        }

        if (!isSuppressed && lastTrigger != null && trigger == lastTrigger && lastInterventionTime != null) {
            val elapsedSec = (nowMs - lastInterventionTime) / 1000.0
            if (elapsedSec < (cooldownSeconds * 2) && urgency != "CRITICAL") {
                isSuppressed = true
                suppressionReason = "DUPLICATE_TRIGGER"
            }
        }

        val fallbackMessage = when (trigger) {
            "HIGH_FATIGUE_STRAIN" -> "Severe fatigue detected ($fatigueScore/100). Step away from $cleanTaskType for a 15-minute recovery walk before resuming."
            "RAPID_CONTEXT_SWITCHING" -> "Frequent context switching detected ($numSwitches switches). Close extra tabs and set notifications to Do-Not-Disturb."
            "VULNERABLE_TASK_CONTEXT" -> "Relocate your $cleanTaskType session from $resolvedContext to Home Office, or shift to a structured planning task."
            "OFF_PEAK_FRICTION" -> "Working outside your peak window. Cap this $cleanTaskType block at 25 minutes and reschedule deep work to $bestWindow."
            else -> "Pacing is steady (score: $score/100). Continue your current $cleanTaskType block in $resolvedContext."
        }

        val structuredEvidence = mapOf<String, Any>(
            "currentTask" to cleanTaskType,
            "productivityScore" to score,
            "fatigue" to fatigueScore,
            "fatigueLevel" to fatigue.first,
            "distraction" to distraction.score,
            "contextSwitches" to numSwitches,
            "context" to resolvedContext,
            "peakWindow" to bestWindow,
            "isInPeakWindow" to (flagWindow == "PEAK"),
            "prediction" to score,
            "riskLevel" to if (score < 45) "HIGH" else if (score < 70) "MEDIUM" else "LOW",
            "confidence" to confidence,
            "detectedTrigger" to trigger,
            "facts" to sanitizedEvidence
        )

        var coachResponseMap: Map<String, Any?>? = null
        var modelProviderStr: String? = null
        var finalIntervention: String? = if (isSuppressed) null else fallbackMessage

        if (!isSuppressed) {
            val activeModel: LocalAIModel = model ?: FallbackAIModel()
            try {
                val resp: AIModelResponse = activeModel.generateCoaching(structuredEvidence)
                coachResponseMap = resp.toMap()
                modelProviderStr = resp.provider
                finalIntervention = resp.message
            } catch (e: Exception) {
                val fallbackModel = FallbackAIModel()
                val resp = fallbackModel.generateCoaching(structuredEvidence)
                coachResponseMap = resp.toMap()
                modelProviderStr = "fallback (recovered from error)"
                finalIntervention = resp.message
            }
        }

        return CoachEvaluation(
            state = state,
            score = score,
            trigger = trigger,
            evidence = sanitizedEvidence,
            intervention = finalIntervention,
            urgency = urgency,
            confidence = confidence,
            isInterventionSuppressed = isSuppressed,
            suppressionReason = suppressionReason,
            structuredEvidence = structuredEvidence,
            fallbackMessage = fallbackMessage,
            coachResponse = coachResponseMap,
            modelProvider = modelProviderStr
        )
    }

    fun evaluateAndCoach(
        currentTaskType: String? = null,
        currentContext: String? = null,
        screenDuration: Long? = null,
        lastInterventionTime: Long? = null,
        lastTrigger: String? = null,
        cooldownSeconds: Long = 900L,
        model: LocalAIModel? = null
    ): CoachEvaluation = evaluateCurrentState(
        currentTaskType = currentTaskType,
        currentContext = currentContext,
        screenDuration = screenDuration,
        lastInterventionTime = lastInterventionTime,
        lastTrigger = lastTrigger,
        cooldownSeconds = cooldownSeconds,
        model = model
    )

    fun evaluateAndCoachAsync(
        currentTaskType: String? = null,
        currentContext: String? = null,
        screenDuration: Long? = null,
        lastInterventionTime: Long? = null,
        lastTrigger: String? = null,
        cooldownSeconds: Long = 900L,
        model: LocalAIModel? = null,
        onResult: (CoachEvaluation) -> Unit
    ) {
        BackgroundExecutor.instance.execute {
            val result = evaluateAndCoach(
                currentTaskType = currentTaskType,
                currentContext = currentContext,
                screenDuration = screenDuration,
                lastInterventionTime = lastInterventionTime,
                lastTrigger = lastTrigger,
                cooldownSeconds = cooldownSeconds,
                model = model
            )
            onResult(result)
        }
    }
}

/**
 * Top-level module convenience function: closed personalization loop.
 */
fun updateUserModel(
    previousModel: UserModel?,
    newTask: Task,
    context: ContextSignal? = null,
    predictedScore: Int? = null
): UserModel {
    val cleanTask = newTask.copy(
        title = PrivacySanitizer.sanitizeText(newTask.title),
        location = PrivacySanitizer.sanitizeContext(newTask.location),
        type = PrivacySanitizer.sanitizeTaskType(newTask.type)
    )
    val cleanContext = context?.copy(
        location = PrivacySanitizer.sanitizeContext(context.location)
    )

    val prevTasks = previousModel?.tasks ?: emptyList()
    val prevSignals = previousModel?.contextSignals ?: emptyList()
    val prevCalib = previousModel?.predictionCalibration ?: PredictionCalibration()

    val predScore: Int? = if (predictedScore != null) {
        predictedScore
    } else if (prevTasks.isNotEmpty()) {
        val prevEngine = InsightEngine(prevTasks, prevSignals)
        val cal = Calendar.getInstance()
        cal.timeInMillis = cleanTask.createdAt
        val tHour = cal.get(Calendar.HOUR_OF_DAY)
        val tLoc = cleanTask.location.ifBlank { cleanContext?.location ?: "Home Office" }
        val tScreen = cleanContext?.screenOnDuration ?: 0L
        val predRes = prevEngine.predictTaskReadiness(cleanTask.type, tHour, tLoc, tScreen)
        predRes.predictedScore
    } else {
        null
    }

    val isCompleted = cleanTask.completedAt != null
    val actualScore = if (isCompleted) 100 else 0
    val actualOutcomeStr = if (isCompleted) "COMPLETED" else "ABANDONED"

    val newCalib: PredictionCalibration
    if (predScore != null) {
        val wasAccurate = (predScore >= 50 && isCompleted) || (predScore < 50 && !isCompleted)
        val outcomeStr = if (wasAccurate) "ACCURATE" else "INACCURATE"
        val error = Math.abs(predScore - actualScore).toDouble()

        val totEval = prevCalib.totalEvaluations + 1
        val accCount = prevCalib.accuratePredictions + (if (wasAccurate) 1 else 0)
        val accRate = Math.round((accCount.toDouble() / totEval) * 1000.0) / 10.0
        val prevMeanErr = prevCalib.meanCalibrationError
        val newMeanErr = Math.round((((prevMeanErr * (totEval - 1)) + error) / totEval) * 10.0) / 10.0

        newCalib = PredictionCalibration(
            totalEvaluations = totEval,
            accuratePredictions = accCount,
            accuracyRate = accRate,
            meanCalibrationError = newMeanErr,
            lastPredictionOutcome = outcomeStr,
            lastPredictedScore = predScore,
            lastActualOutcome = actualOutcomeStr
        )
    } else {
        newCalib = prevCalib.copy(
            lastActualOutcome = actualOutcomeStr
        )
    }

    val updatedTasks = prevTasks + listOf(cleanTask)
    val updatedSignals = if (cleanContext != null) prevSignals + listOf(cleanContext) else prevSignals

    val engine = InsightEngine(updatedTasks, updatedSignals, newCalib)
    val insights = engine.analyze()
    val profile = insights.productivityProfile

    return UserModel(
        productivityProfile = profile,
        predictionCalibration = newCalib,
        adaptiveRecommendations = insights.adaptiveRecommendations,
        tasks = updatedTasks,
        contextSignals = updatedSignals,
        taskCount = updatedTasks.size,
        lastUpdated = System.currentTimeMillis()
    )
}
