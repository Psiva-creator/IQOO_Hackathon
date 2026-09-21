package com.iqoo.productivity.engine

import com.iqoo.productivity.model.Task
import com.iqoo.productivity.model.TaskType
import java.util.Calendar

data class ContextSignal(
    val timestamp: Long,
    val appCategory: String,
    val location: String = "Home Office",
    val screenOnDuration: Long = 0L // in seconds
)

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
    val coachEvaluation: CoachEvaluation? = null
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
    val fallbackMessage: String = ""
)

/**
 * On-Device Habit & Productivity Insight Engine
 * Pure Kotlin, zero external dependencies, 100% on-device deterministic analytics.
 * Complies strictly with contracts/insight.schema.json.
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
        val procrastinationTrigger = detectProcrastinationTrigger()
        val contextInsights = analyzeContexts()
        val bestContextStr = formatBestContext(contextInsights)
        val fatigue = detectFatigue()
        val distraction = detectDistractionSensitivity()
        val score = calculateProductivityScore()
        val heatmap = generateHourlyHeatmap()
        val taskTypeAnalysis = analyzeTaskTypes()
        val profile = buildProductivityProfile(peakHour, contextInsights, fatigue, distraction, heatmap, taskTypeAnalysis)
        val adaptiveRecs = generateAdaptiveRecommendations(profile, contextInsights, fatigue, distraction)

        val primaryRec = adaptiveRecs.first()
        val topRecommendation = "${primaryRec.advice} ${primaryRec.reason}"

        val pred = if (targetTaskType != null) {
            predictTaskReadiness(targetTaskType, currentHour, currentContext, recentScreenDuration)
        } else null

        return InsightResult(
            peakHour = peakHour,
            procrastinationTrigger = procrastinationTrigger,
            bestContext = bestContextStr,
            recommendation = topRecommendation,
            productivityScore = score,
            confidenceLevel = confidence,
            hourlyHeatmap = heatmap,
            fatigueLevel = fatigue.first,
            fatigueScore = fatigue.second,
            explanation = fatigue.third,
            contextInsights = contextInsights,
            distractionSensitivity = distraction,
            productivityProfile = profile,
            adaptiveRecommendations = adaptiveRecs,
            taskPrediction = pred
        )
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
        val typeTotal = mutableMapOf<TaskType, Int>()
        val typeFailed = mutableMapOf<TaskType, Int>()

        for (task in tasks) {
            val type = task.type
            typeTotal[type] = (typeTotal[type] ?: 0) + 1

            if (task.completedAt == null) {
                typeFailed[type] = (typeFailed[type] ?: 0) + 1
            }
        }

        var worstType: TaskType? = null
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
            val typeName = worstType.name.lowercase().replaceFirstChar { it.uppercase() }
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

    private fun formatBestContext(contextInsights: List<ContextInsight>): String {
        if (contextInsights.isEmpty()) return "Home Office (Consistent completion)"
        val best = contextInsights.firstOrNull { it.totalTasks >= 2 } ?: contextInsights.first()
        return "${best.context} (${best.completionRate}% completion across ${best.totalTasks} sessions)"
    }

    private fun detectFatigue(): Triple<String, Int, String> {
        var screenPts = 0
        var maxScreenSec = 0L
        if (contextSignals.isNotEmpty()) {
            maxScreenSec = contextSignals.maxOfOrNull { it.screenOnDuration } ?: 0L
            val avgScreenSec = contextSignals.map { it.screenOnDuration }.average()
            if (maxScreenSec >= 7200 || avgScreenSec >= 4500) {
                screenPts = 30
            } else if (maxScreenSec >= 4500 || avgScreenSec >= 3000) {
                screenPts = 20
            } else if (maxScreenSec >= 2700) {
                screenPts = 10
            }
        } else {
            val avgTaskDur = if (tasks.isNotEmpty()) tasks.map { it.duration }.average() else 0.0
            if (avgTaskDur >= 3600) screenPts = 20
            else if (avgTaskDur >= 2400) screenPts = 10
            else if (avgTaskDur >= 1200) screenPts = 5
        }

        val cal = Calendar.getInstance()
        val morningTasks = tasks.filter {
            cal.timeInMillis = it.createdAt
            cal.get(Calendar.HOUR_OF_DAY) < 13
        }
        val afternoonTasks = tasks.filter {
            cal.timeInMillis = it.createdAt
            cal.get(Calendar.HOUR_OF_DAY) >= 13
        }

        var completionDropPts = 0
        var mRate = 0.0
        var aRate = 0.0
        var drop = 0.0

        if (morningTasks.isNotEmpty() && afternoonTasks.isNotEmpty()) {
            val mComp = morningTasks.count { it.completedAt != null }
            val aComp = afternoonTasks.count { it.completedAt != null }
            mRate = mComp.toDouble() / morningTasks.size
            aRate = aComp.toDouble() / afternoonTasks.size
            drop = mRate - aRate

            if (drop >= 0.40) completionDropPts = 30
            else if (drop >= 0.20) completionDropPts = 20
            else if (drop >= 0.10) completionDropPts = 10
        }

        var durationShrinkPts = 0
        var mDur = 0.0
        var aDur = 0.0
        if (morningTasks.isNotEmpty() && afternoonTasks.isNotEmpty()) {
            mDur = morningTasks.map { it.duration }.average()
            aDur = afternoonTasks.map { it.duration }.average()
            if (mDur > 0 && (aDur / mDur) <= 0.50) durationShrinkPts = 20
            else if (mDur > 0 && (aDur / mDur) <= 0.75) durationShrinkPts = 10
        }

        var switchingPts = 0
        var nonProdSignals = 0
        if (contextSignals.isNotEmpty()) {
            nonProdSignals = contextSignals.count { it.appCategory in listOf("Social", "Entertainment") }
            val nonProdRatio = nonProdSignals.toDouble() / contextSignals.size
            if (nonProdRatio >= 0.35) switchingPts = 20
            else if (nonProdRatio >= 0.15) switchingPts = 10
        } else {
            val sorted = tasks.sortedBy { it.createdAt }
            var switches = 0
            for (i in 1 until sorted.size) {
                val gap = (sorted[i].createdAt - sorted[i - 1].createdAt) / 1000
                if (gap < 2700 && sorted[i].type != sorted[i - 1].type) {
                    switches++
                }
            }
            if (switches >= 4) switchingPts = 15
            else if (switches >= 2) switchingPts = 10
        }

        val totalScore = (screenPts + completionDropPts + durationShrinkPts + switchingPts).coerceIn(0, 100)
        val level = when {
            totalScore >= 65 -> "HIGH"
            totalScore >= 35 -> "MEDIUM"
            else -> "LOW"
        }

        val explanations = mutableListOf<String>()
        if (drop >= 0.20) {
            explanations.add("completion rate drops by ${(drop * 100).toInt()}% in the afternoon (${(mRate * 100).toInt()}% morning vs ${(aRate * 100).toInt()}% afternoon)")
        }
        if (mDur > 0 && (aDur / mDur) <= 0.75) {
            explanations.add("focus sessions shorten by ${((1.0 - aDur / mDur) * 100).toInt()}% after mid-day")
        }
        if (maxScreenSec >= 4500) {
            explanations.add("prolonged continuous screen time exceeds ${maxScreenSec / 60} minutes")
        } else if (screenPts >= 10) {
            explanations.add("extended cumulative focus session duration detected")
        }
        if (nonProdSignals > 0) {
            explanations.add("non-productive app category switches observed ($nonProdSignals signals)")
        } else if (switchingPts >= 10) {
            explanations.add("frequent consecutive task switching observed")
        }

        val explanation = if (explanations.isEmpty()) {
            "Fatigue is $level (score: $totalScore/100). Focus duration and completion rates remain stable across work blocks."
        } else {
            "Fatigue is $level (score: $totalScore/100). " + explanations.joinToString("; ").replaceFirstChar { it.uppercase() } + "."
        }

        return Triple(level, totalScore, explanation)
    }

    private fun detectDistractionSensitivity(): DistractionSensitivity {
        val typeFailures = mutableMapOf<TaskType, Pair<Int, Int>>()
        for (task in tasks) {
            val curr = typeFailures.getOrPut(task.type) { Pair(0, 0) }
            val failInc = if (task.completedAt == null) 1 else 0
            typeFailures[task.type] = Pair(curr.first + 1, curr.second + failInc)
        }

        val vulnerable = mutableListOf<String>()
        for ((type, stats) in typeFailures) {
            if (stats.first >= 2) {
                val failRate = stats.second.toDouble() / stats.first
                if (failRate >= 0.40) {
                    vulnerable.add(type.name.lowercase())
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
        val tasksByType = mutableMapOf<TaskType, MutableList<Pair<Task, Double>>>()
        for (i in tasks.indices) {
            val task = tasks[i]
            val w = weights[i]
            tasksByType.getOrPut(task.type) { mutableListOf() }.add(Pair(task, w))
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
                    taskType = type.name.lowercase(),
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

    private fun detectWeakestFocusWindow(): String {
        val cal = Calendar.getInstance()
        val hourlyAttempts = mutableMapOf<Int, Int>()
        val hourlyFailed = mutableMapOf<Int, Int>()

        for (task in tasks) {
            cal.timeInMillis = task.createdAt
            val h = cal.get(Calendar.HOUR_OF_DAY)
            hourlyAttempts[h] = (hourlyAttempts[h] ?: 0) + 1
            if (task.completedAt == null) {
                hourlyFailed[h] = (hourlyFailed[h] ?: 0) + 1
            }
        }

        var worstHour: Int? = null
        var highestFailRate = 0.0

        for (h in 0 until 24) {
            val attInWindow = (hourlyAttempts[h] ?: 0) + (hourlyAttempts[(h + 1) % 24] ?: 0)
            val failInWindow = (hourlyFailed[h] ?: 0) + (hourlyFailed[(h + 1) % 24] ?: 0)
            if (attInWindow >= 2) {
                val rate = failInWindow.toDouble() / attInWindow
                if (rate > highestFailRate) {
                    highestFailRate = rate
                    worstHour = h
                }
            }
        }

        return if (worstHour != null && highestFailRate >= 0.30) {
            String.format("%02d:00 - %02d:00", worstHour, (worstHour + 2) % 24)
        } else {
            "None detected"
        }
    }

    private fun buildProductivityProfile(
        peakHour: String,
        contextInsights: List<ContextInsight>,
        fatigue: Triple<String, Int, String>,
        distraction: DistractionSensitivity,
        heatmap: Map<Int, Int>,
        taskTypeAnalysis: List<TaskTypeAnalysis>
    ): ProductivityProfile {
        val total = tasks.size
        val profileConfidence = calculateProfileConfidence()

        if (total < 5) {
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
                taskTypeAnalysis = taskTypeAnalysis
            )
        }

        val bestWindow = peakHour.split("(")[0].trim()
        val bestTypes = taskTypeAnalysis.filter { it.completionRate >= 70.0 && it.totalSessions >= 2 }.map { it.taskType }
        val bestCtx = contextInsights.firstOrNull { it.totalTasks >= 2 && it.status == "Optimal" }?.context ?: (contextInsights.firstOrNull()?.context ?: "Home Office")
        val weakestWindow = detectWeakestFocusWindow()
        val peakScore = heatmap.values.maxOrNull() ?: 0
        val weights = getRecencyWeights()
        val weightedCompleted = tasks.indices.filter { tasks[it].completedAt != null }.sumOf { weights[it] }
        val totalWeight = weights.sum()
        val avgCompletion = if (totalWeight > 0.0) Math.round((weightedCompleted / totalWeight) * 1000.0) / 10.0 else 0.0

        val fatigueScore = fatigue.second
        val fatiguePattern = when {
            fatigueScore >= 65 -> "Severe fatigue peaks after ${weakestWindow.split(" - ")[0]} (score: $fatigueScore/100) after extended screen sessions."
            fatigueScore >= 35 -> "Moderate fatigue appears in late afternoon (score: $fatigueScore/100) with focus durations shrinking."
            else -> "Stable energy profile across daytime work blocks with minimal session shrinkage."
        }

        val distractionPattern = when {
            distraction.vulnerableCategories.isNotEmpty() && distraction.triggerAppCategories.isNotEmpty() ->
                "High vulnerability on ${distraction.vulnerableCategories.joinToString(", ")} when ${distraction.triggerAppCategories.joinToString(", ")} apps are accessed."
            distraction.vulnerableCategories.isNotEmpty() ->
                "${distraction.vulnerableCategories.joinToString(", ").replaceFirstChar { it.uppercase() }} tasks show elevated abandonment outside optimal environments."
            else -> "Low distraction susceptibility across tracked contexts."
        }

        return ProductivityProfile(
            bestFocusWindow = bestWindow,
            bestTaskTypes = bestTypes,
            bestContext = bestCtx,
            weakestFocusWindow = weakestWindow,
            peakProductivityScore = peakScore,
            averageCompletionRate = avgCompletion,
            fatiguePattern = fatiguePattern,
            distractionPattern = distractionPattern,
            profileConfidence = profileConfidence,
            taskTypeAnalysis = taskTypeAnalysis
        )
    }

    private fun generateAdaptiveRecommendations(
        profile: ProductivityProfile,
        contextInsights: List<ContextInsight>,
        fatigue: Triple<String, Int, String>,
        distraction: DistractionSensitivity
    ): List<AdaptiveRecommendation> {
        val candidates = mutableListOf<Pair<Int, AdaptiveRecommendation>>()

        if (profile.bestFocusWindow != "Insufficient Data" && profile.bestTaskTypes.isNotEmpty()) {
            val primaryType = profile.bestTaskTypes.first()
            val typeStat = profile.taskTypeAnalysis.find { it.taskType == primaryType }
            val rateStr = if (typeStat != null) "${typeStat.completionRate.toInt()}%" else "peak"
            candidates.add(
                Pair(
                    95,
                    AdaptiveRecommendation(
                        title = "Protect Peak ${primaryType.replaceFirstChar { it.uppercase() }} Window",
                        advice = "Schedule demanding $primaryType tasks between ${profile.bestFocusWindow} in ${profile.bestContext}.",
                        reason = "Your $primaryType completion rate reaches $rateStr in ${profile.bestContext} during this window.",
                        priority = "HIGH",
                        impact = "HIGH"
                    )
                )
            )
        }

        val fatigueScore = fatigue.second
        if (fatigueScore >= 35) {
            val isHigh = fatigueScore >= 65
            val weakStart = if (profile.weakestFocusWindow != "None detected") profile.weakestFocusWindow.split(" - ")[0] else "15:00"
            candidates.add(
                Pair(
                    if (isHigh) 90 else 70,
                    AdaptiveRecommendation(
                        title = "Fatigue Break Pacing",
                        advice = "Cap afternoon focus sessions at 45 minutes and step away before $weakStart.",
                        reason = profile.fatiguePattern,
                        priority = if (isHigh) "HIGH" else "MEDIUM",
                        impact = if (isHigh) "HIGH" else "MEDIUM"
                    )
                )
            )
        }

        if (contextInsights.size >= 2) {
            val bestC = contextInsights.first()
            val worstC = contextInsights.last()
            if (bestC.completionRate - worstC.completionRate >= 25.0) {
                val vulnerableType = distraction.vulnerableCategories.firstOrNull() ?: "complex"
                candidates.add(
                    Pair(
                        80,
                        AdaptiveRecommendation(
                            title = "Shift Context for Vulnerable Tasks",
                            advice = "Relocate $vulnerableType sessions from ${worstC.context} to ${bestC.context}.",
                            reason = "Completion rate is ${bestC.completionRate}% in ${bestC.context} versus ${worstC.completionRate}% in ${worstC.context}.",
                            priority = "MEDIUM",
                            impact = if (bestC.completionRate - worstC.completionRate >= 40.0) "HIGH" else "MEDIUM"
                        )
                    )
                )
            }
        }

        if (distraction.level in listOf("HIGH", "MEDIUM") && distraction.triggerAppCategories.isNotEmpty()) {
            val triggers = distraction.triggerAppCategories.joinToString(", ")
            candidates.add(
                Pair(
                    75,
                    AdaptiveRecommendation(
                        title = "Silence Interrupting App Categories",
                        advice = "Enable Do Not Disturb to block $triggers alerts during focus blocks.",
                        reason = profile.distractionPattern,
                        priority = "MEDIUM",
                        impact = "MEDIUM"
                    )
                )
            )
        }

        if (candidates.isEmpty()) {
            candidates.add(
                Pair(
                    50,
                    AdaptiveRecommendation(
                        title = "Maintain Rhythm",
                        advice = "Continue consistent task tracking in your ${profile.bestFocusWindow} focus block.",
                        reason = "Current session distribution shows stable pacing and low distraction interference.",
                        priority = "LOW",
                        impact = "LOW"
                    )
                )
            )
        }

        candidates.sortByDescending { it.first }
        return candidates.take(3).map { it.second }
    }

    private fun calculateProductivityScore(): Int {
        val total = tasks.size
        if (total == 0) return 0
        val weights = getRecencyWeights()
        val weightedCompleted = tasks.indices.filter { tasks[it].completedAt != null }.sumOf { weights[it] }
        val totalWeight = weights.sum()
        return if (totalWeight > 0.0) ((weightedCompleted / totalWeight) * 100).toInt().coerceIn(0, 100) else 0
    }

    private fun calculateConfidence(): String {
        val count = tasks.size
        return when {
            count < 5 -> "Calibrating"
            count < 20 -> "Medium"
            else -> "High"
        }
    }

    private fun calculateProfileConfidence(): String {
        val count = tasks.size
        return when {
            count < 5 -> "LOW"
            count <= 15 -> "MEDIUM"
            else -> "HIGH"
        }
    }

    private fun generateHourlyHeatmap(): Map<Int, Int> {
        val calendar = Calendar.getInstance()
        val weights = getRecencyWeights()
        val attempts = mutableMapOf<Int, Double>()
        val completed = mutableMapOf<Int, Double>()

        for (i in tasks.indices) {
            val task = tasks[i]
            calendar.timeInMillis = task.createdAt
            val hour = calendar.get(Calendar.HOUR_OF_DAY)
            attempts[hour] = (attempts[hour] ?: 0.0) + weights[i]
            if (task.completedAt != null) {
                completed[hour] = (completed[hour] ?: 0.0) + weights[i]
            }
        }

        return (0..23).associateWith { hour ->
            val att = attempts[hour] ?: 0.0
            val comp = completed[hour] ?: 0.0
            if (att == 0.0) 0 else ((comp / att) * 100).toInt()
        }
    }

    fun predictTaskReadiness(
        taskType: String,
        currentHour: Int? = null,
        currentContext: String? = null,
        recentScreenDuration: Long? = null
    ): TaskPrediction {
        val resolvedHour = currentHour ?: if (contextSignals.isNotEmpty()) {
            val cal = Calendar.getInstance()
            cal.timeInMillis = contextSignals.last().timestamp
            cal.get(Calendar.HOUR_OF_DAY)
        } else if (tasks.isNotEmpty()) {
            val cal = Calendar.getInstance()
            cal.timeInMillis = tasks.last().createdAt
            cal.get(Calendar.HOUR_OF_DAY)
        } else {
            Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        }

        val resolvedContext = currentContext ?: if (contextSignals.isNotEmpty()) {
            contextSignals.last().location
        } else if (tasks.isNotEmpty()) {
            tasks.last().location ?: "Home Office"
        } else {
            "Home Office"
        }

        val resolvedScreenDuration = recentScreenDuration ?: if (contextSignals.isNotEmpty()) {
            contextSignals.last().screenOnDuration
        } else {
            0L
        }

        val totalTasks = tasks.size
        val typeTasks = tasks.filter { it.type.name.equals(taskType, ignoreCase = true) }
        val totalTypeTasks = typeTasks.size

        if (totalTasks == 0) {
            return TaskPrediction(
                taskType = taskType,
                predictedScore = 50,
                confidence = "LOW",
                riskLevel = "MEDIUM",
                bestAlternativeWindow = "09:00 - 11:00",
                reason = "No historical sessions logged. Calibration required to establish baseline readiness for $taskType.",
                recommendation = "Start a 25-minute calibration block for $taskType to establish baseline metrics."
            )
        }

        if (totalTasks < 5 || totalTypeTasks == 0) {
            val completedAll = tasks.count { it.completedAt != null }
            val overallRate = completedAll.toDouble() / totalTasks
            val provisionalScore = (overallRate * 50.0 + 20.0).toInt().coerceIn(35, 65)
            val riskLevel = if (provisionalScore >= 60) "LOW" else if (provisionalScore < 40) "HIGH" else "MEDIUM"
            val bestWindow = "09:00 - 11:00"
            val reason = if (totalTypeTasks == 0) {
                "No historical sessions recorded for '$taskType'. Provisional score based on overall user completion rate (${(overallRate * 100).toInt()}%)."
            } else {
                val s = if (totalTypeTasks > 1) "s" else ""
                "Insufficient sample size ($totalTypeTasks logged session$s for '$taskType'). Baseline readiness estimate."
            }
            val rec = if (totalTypeTasks == 0) {
                "Log at least 3 $taskType sessions to calibrate high-confidence predictive readiness."
            } else {
                "Continue tracking $taskType sessions across various hours to establish personalized forecasts."
            }
            return TaskPrediction(
                taskType = taskType,
                predictedScore = provisionalScore,
                confidence = "LOW",
                riskLevel = riskLevel,
                bestAlternativeWindow = bestWindow,
                reason = reason,
                recommendation = rec
            )
        }

        // 2. Historical Task-Type Performance (0..35 points)
        val typeCompleted = typeTasks.count { it.completedAt != null }
        val typeCompRate = typeCompleted.toDouble() / totalTypeTasks
        val scoreType = typeCompRate * 35.0

        // 3. Time-of-Day Alignment (0..25 points)
        val cal = Calendar.getInstance()
        val typeHourTasks = typeTasks.filter {
            cal.timeInMillis = it.createdAt
            val h = cal.get(Calendar.HOUR_OF_DAY)
            Math.abs(h - resolvedHour) <= 1
        }
        val scoreTime = if (typeHourTasks.isNotEmpty()) {
            val comp = typeHourTasks.count { it.completedAt != null }.toDouble() / typeHourTasks.size
            comp * 25.0
        } else {
            val heatmap = generateHourlyHeatmap()
            var hourRate = (heatmap[resolvedHour] ?: 0) / 100.0
            val hourAttempts = tasks.count {
                cal.timeInMillis = it.createdAt
                cal.get(Calendar.HOUR_OF_DAY) == resolvedHour
            }
            if (hourAttempts == 0) {
                hourRate = when (resolvedHour) {
                    in 8..12 -> 0.8
                    in 13..17 -> 0.45
                    in 18..21 -> 0.65
                    else -> 0.25
                }
            }
            hourRate * 25.0
        }

        // 4. Context Alignment (0..20 points)
        val contextInsights = analyzeContexts()
        val matchingCtx = contextInsights.firstOrNull { it.context.equals(resolvedContext, ignoreCase = true) }
        val typeInCtx = typeTasks.filter { (it.location ?: "Home Office").equals(resolvedContext, ignoreCase = true) }
        val scoreContext = if (typeInCtx.isNotEmpty()) {
            val comp = typeInCtx.count { it.completedAt != null }.toDouble() / typeInCtx.size
            comp * 20.0
        } else if (matchingCtx != null) {
            (matchingCtx.completionRate / 100.0) * 20.0
        } else {
            10.0
        }

        // 5. Base Readiness Offset (20 points)
        val scoreBase = 20.0

        // 6. Fatigue & Screen Strain Penalty (0..25 points)
        val fatigue = detectFatigue()
        val fatigueScorePts = (fatigue.second / 100.0) * 15.0
        val screenPts = when {
            resolvedScreenDuration >= 5400L -> 10.0
            resolvedScreenDuration >= 3600L -> 7.0
            resolvedScreenDuration >= 2400L -> 4.0
            resolvedScreenDuration >= 1200L -> 2.0
            else -> 0.0
        }
        val totalFatiguePenalty = Math.min(25.0, fatigueScorePts + screenPts)

        // 7. Distraction & Context Vulnerability Penalty (0..15 points)
        val distraction = detectDistractionSensitivity()
        var distractionPenalty = 0.0
        val isVulnerable = distraction.vulnerableCategories.any { it.equals(taskType, ignoreCase = true) }
        if (isVulnerable) {
            if (matchingCtx?.status == "Suboptimal") {
                distractionPenalty += 12.0
            } else {
                distractionPenalty += 6.0
            }
        }
        if (distraction.level == "HIGH") {
            distractionPenalty += 3.0
        }
        val totalDistractionPenalty = Math.min(15.0, distractionPenalty)

        // 8. Score Synthesis
        val rawScore = scoreBase + scoreType + scoreTime + scoreContext - totalFatiguePenalty - totalDistractionPenalty
        val predictedScore = Math.round(Math.max(0.0, Math.min(100.0, rawScore))).toInt()

        // 9. Risk Level & Confidence
        val riskLevel = when {
            predictedScore >= 70 -> "LOW"
            predictedScore >= 45 -> "MEDIUM"
            else -> "HIGH"
        }

        val confidence = when {
            totalTypeTasks >= 3 && totalTasks >= 5 -> "HIGH"
            totalTypeTasks >= 1 && totalTasks >= 5 -> "MEDIUM"
            else -> "LOW"
        }

        // 10. Best Alternative Window
        val taskTypes = analyzeTaskTypes()
        val typeStat = taskTypes.firstOrNull { it.taskType.equals(taskType, ignoreCase = true) }
        val bestWindow = if (typeStat != null && typeStat.strongestWindow != "Insufficient data") {
            typeStat.strongestWindow
        } else {
            detectPeakHour().split("(")[0].trim()
        }

        var windowStart = 9
        var windowEnd = 11
        try {
            val parts = bestWindow.split(" - ")
            windowStart = parts[0].split(":")[0].toInt()
            windowEnd = parts[1].split(":")[0].toInt()
        } catch (e: Exception) {
            windowStart = 9
            windowEnd = 11
        }

        val isCurrentlyInBestWindow = if (windowStart < windowEnd) {
            resolvedHour in windowStart until windowEnd
        } else {
            resolvedHour >= windowStart || resolvedHour < windowEnd
        }

        val bestAltWindow = if (isCurrentlyInBestWindow) {
            if (riskLevel == "LOW") {
                "Current window ($bestWindow) is optimal"
            } else {
                "Tomorrow morning ($bestWindow)"
            }
        } else {
            bestWindow
        }

        // 11. Explainable Reason
        val positives = mutableListOf<String>()
        val negatives = mutableListOf<String>()

        if (typeCompRate >= 0.75) {
            positives.add("${taskType.replaceFirstChar { it.uppercase() }} completion is high (${(typeCompRate * 100).toInt()}%)")
        } else if (typeCompRate <= 0.40) {
            negatives.add("${taskType.replaceFirstChar { it.uppercase() }} completion is historically low (${(typeCompRate * 100).toInt()}%)")
        }

        if (scoreTime >= 18.0) {
            positives.add(String.format("time-of-day alignment is optimal (%02d:00)", resolvedHour))
        } else if (scoreTime <= 10.0) {
            negatives.add(String.format("hour (%02d:00) is outside your peak focus", resolvedHour))
        }

        if (scoreContext >= 15.0) {
            positives.add("environment '$resolvedContext' is high-performing")
        } else if (matchingCtx?.status == "Suboptimal") {
            negatives.add("environment '$resolvedContext' has high abandonment")
        }

        if (fatigue.second >= 35 || resolvedScreenDuration >= 3600L) {
            negatives.add("fatigue is elevated (score: ${fatigue.second}/100, ${resolvedScreenDuration / 60}m screen time)")
        }

        if (isVulnerable && matchingCtx?.status == "Suboptimal") {
            negatives.add("$taskType is highly vulnerable to distractions in $resolvedContext")
        }

        val reason = when (riskLevel) {
            "HIGH" -> {
                val negStr = if (negatives.isNotEmpty()) negatives.joinToString("; ") else "historical completion is significantly lower during this time and context"
                "${taskType.replaceFirstChar { it.uppercase() }} now has HIGH risk ($predictedScore/100): $negStr. Your $taskType completion is significantly higher during $bestWindow."
            }
            "MEDIUM" -> {
                val mixed = if (positives.isNotEmpty() || negatives.isNotEmpty()) {
                    (positives.take(1) + negatives.take(2)).joinToString("; ")
                } else {
                    "balanced conditions with minor timing or fatigue friction"
                }
                "${taskType.replaceFirstChar { it.uppercase() }} readiness is MODERATE ($predictedScore/100): $mixed."
            }
            else -> {
                val posStr = if (positives.isNotEmpty()) positives.joinToString("; ") else "strong historical focus metrics in $resolvedContext"
                "Optimal conditions for $taskType ($predictedScore/100): $posStr."
            }
        }

        val bestCtxName = contextInsights.firstOrNull()?.context ?: "Home Office"
        val recommendation = when (riskLevel) {
            "HIGH" -> "Consider postponing $taskType to $bestAltWindow in $bestCtxName. Take a 15-minute break now to recover cognitive energy."
            "MEDIUM" -> "Proceed with a focused 25-minute sprint for $taskType. Minimize distractions and take a short recovery break afterward."
            else -> "Start $taskType now. You are in optimal conditions for sustained focus in $resolvedContext."
        }

        return TaskPrediction(
            taskType = taskType,
            predictedScore = predictedScore,
            confidence = confidence,
            riskLevel = riskLevel,
            bestAlternativeWindow = bestAltWindow,
            reason = reason,
            recommendation = recommendation
        )
    }

    fun updateUserModel(newTask: Task, context: ContextSignal? = null, predictedScore: Int? = null): UserModel {
        val prevModel = UserModel(
            productivityProfile = this.analyze().productivityProfile,
            predictionCalibration = this.predictionCalibration,
            adaptiveRecommendations = this.analyze().adaptiveRecommendations,
            tasks = this.tasks,
            contextSignals = this.contextSignals,
            taskCount = this.tasks.size
        )
        val updated = com.iqoo.productivity.engine.updateUserModel(prevModel, newTask, context, predictedScore)
        this.tasks = updated.tasks
        this.contextSignals = updated.contextSignals
        this.predictionCalibration = updated.predictionCalibration
        return updated
    }

    fun evaluateCurrentState(
        taskType: String = "coding",
        currentHour: Int? = null,
        context: String? = null,
        screenDuration: Long = 0L,
        recentActivity: List<ContextSignal> = emptyList(),
        lastInterventionTime: Long? = null,
        lastTrigger: String? = null,
        currentTime: Long? = null,
        cooldownSeconds: Long = 900L
    ): CoachEvaluation {
        val nowMs = currentTime ?: System.currentTimeMillis()

        // 1. Resolve Context
        val resolvedContext = context ?: if (contextSignals.isNotEmpty()) {
            contextSignals.last().location
        } else if (tasks.isNotEmpty()) {
            tasks.last().location ?: "Home Office"
        } else {
            "Home Office"
        }

        // 2. Resolve Current Hour
        val resolvedHour = currentHour ?: run {
            val cal = Calendar.getInstance()
            cal.timeInMillis = nowMs
            cal.get(Calendar.HOUR_OF_DAY)
        }

        // 3. Analyze Recent Activity
        var numSwitches = 0
        var nonProdCount = 0
        if (recentActivity.isNotEmpty()) {
            for (i in recentActivity.indices) {
                val cat = recentActivity[i].appCategory
                if (cat in listOf("Social", "Entertainment", "Communication")) {
                    nonProdCount++
                }
                if (i > 0 && cat != recentActivity[i - 1].appCategory) {
                    numSwitches++
                }
            }
        } else if (contextSignals.isNotEmpty()) {
            val recentSlice = contextSignals.takeLast(10).filter {
                Math.abs(nowMs - it.timestamp) <= 1800000L
            }
            for (i in recentSlice.indices) {
                val cat = recentSlice[i].appCategory
                if (cat in listOf("Social", "Entertainment", "Communication")) {
                    nonProdCount++
                }
                if (i > 0 && cat != recentSlice[i - 1].appCategory) {
                    numSwitches++
                }
            }
        }

        // 4. Baseline Analytics
        val fatigue = detectFatigue()
        val distraction = detectDistractionSensitivity()
        val contextInsights = analyzeContexts()
        val heatmap = generateHourlyHeatmap()
        val taskTypes = analyzeTaskTypes()
        val peakHourStr = detectPeakHour()
        val profile = buildProductivityProfile(peakHourStr, contextInsights, fatigue, distraction, heatmap, taskTypes)
        val bestWindow = profile.bestFocusWindow
        val weakestWindow = profile.weakestFocusWindow
        val bestContext = profile.bestContext
        val confidence = profile.profileConfidence

        // 5. Evaluate Telemetry & Compute Evidence
        val evidence = mutableListOf<String>()
        var rawScore = 100
        val screenDurationMin = screenDuration / 60

        var flagScreen = "NONE"
        var flagSwitching = "NONE"
        var flagFatigue = "NONE"
        var flagWindow = "NONE"
        var flagContext = "NONE"

        // A. Screen Time
        if (screenDuration >= 7200L) {
            rawScore -= 40
            evidence.add("Continuous screen time exceeds ${screenDurationMin} minutes (critical limit)")
            flagScreen = "CRITICAL"
        } else if (screenDuration >= 5400L) {
            rawScore -= 25
            evidence.add("Extended continuous screen time: ${screenDurationMin} minutes without a break")
            flagScreen = "HIGH"
        } else if (screenDuration >= 2700L) {
            rawScore -= 15
            evidence.add("Continuous screen duration reaching ${screenDurationMin} minutes")
            flagScreen = "MEDIUM"
        } else if (screenDuration >= 1800L) {
            rawScore -= 5
            evidence.add("Screen-on duration: ${screenDurationMin} minutes")
            flagScreen = "LOW"
        }

        // B. Switching & Non-productive apps
        if (numSwitches >= 6 || nonProdCount >= 4) {
            rawScore -= 25
            evidence.add("$numSwitches context switches in recent activity with $nonProdCount non-productive interruptions")
            flagSwitching = "HIGH"
        } else if (numSwitches >= 3 || nonProdCount >= 2) {
            rawScore -= 15
            evidence.add("Frequent context switching detected ($numSwitches switches, $nonProdCount non-productive signals)")
            flagSwitching = "MEDIUM"
        } else if (nonProdCount >= 1 || numSwitches >= 1) {
            rawScore -= 5
            evidence.add("Minor context disruption observed ($nonProdCount non-productive signals)")
            flagSwitching = "LOW"
        }

        // C. Fatigue State
        val fatigueScore = fatigue.second
        if (fatigueScore >= 65) {
            rawScore -= 25
            evidence.add("Cognitive fatigue is elevated ($fatigueScore/100, HIGH)")
            flagFatigue = "HIGH"
        } else if (fatigueScore >= 35) {
            rawScore -= 15
            evidence.add("Moderate fatigue accumulation ($fatigueScore/100)")
            flagFatigue = "MEDIUM"
        } else {
            flagFatigue = "LOW"
        }

        // D. Time-of-Day Window
        var isInBestWindow = false
        try {
            val parts = bestWindow.split(" - ")
            val wStart = parts[0].split(":")[0].toInt()
            val wEnd = parts[1].split(":")[0].toInt()
            isInBestWindow = if (wStart < wEnd) resolvedHour in wStart until wEnd else (resolvedHour >= wStart || resolvedHour < wEnd)
        } catch (e: Exception) {
            isInBestWindow = resolvedHour in 9 until 11
        }

        var isInWeakestWindow = false
        if (weakestWindow != "None detected" && weakestWindow != "Insufficient Data") {
            try {
                val wparts = weakestWindow.split(" - ")
                val wwStart = wparts[0].split(":")[0].toInt()
                val wwEnd = wparts[1].split(":")[0].toInt()
                isInWeakestWindow = if (wwStart < wwEnd) resolvedHour in wwStart until wwEnd else (resolvedHour >= wwStart || resolvedHour < wwEnd)
            } catch (e: Exception) {
                isInWeakestWindow = false
            }
        }

        if (isInWeakestWindow) {
            rawScore -= 20
            evidence.add(String.format("Working at %02d:00 in your historically weakest window (%s)", resolvedHour, weakestWindow))
            flagWindow = "WEAKEST"
        } else if (!isInBestWindow) {
            rawScore -= 10
            evidence.add(String.format("Working at %02d:00 outside your peak focus window (%s)", resolvedHour, bestWindow))
            flagWindow = "OFF_PEAK"
        } else {
            rawScore += 5
            evidence.add(String.format("Working at %02d:00 inside your peak focus window (%s)", resolvedHour, bestWindow))
            flagWindow = "PEAK"
        }

        // E. Context & Vulnerable Task
        val isVulnerable = distraction.vulnerableCategories.any { it.equals(taskType, ignoreCase = true) }
        val matchingCtx = contextInsights.firstOrNull { it.context.equals(resolvedContext, ignoreCase = true) }

        if (isVulnerable && matchingCtx?.status == "Suboptimal") {
            rawScore -= 20
            evidence.add("'${taskType.replaceFirstChar { it.uppercase() }}' is highly vulnerable in '$resolvedContext' (${matchingCtx.completionRate}% completion)")
            flagContext = "VULNERABLE_SUBOPTIMAL"
        } else if (matchingCtx?.status == "Suboptimal") {
            rawScore -= 10
            evidence.add("Environment '$resolvedContext' has historically low completion (${matchingCtx.completionRate}%)")
            flagContext = "SUBOPTIMAL"
        } else if (matchingCtx?.status == "Optimal") {
            rawScore += 5
            evidence.add("Environment '$resolvedContext' is optimal (${matchingCtx.completionRate}% completion)")
            flagContext = "OPTIMAL"
        } else {
            flagContext = "NEUTRAL"
        }

        // 6. Score & State Classification
        val score = rawScore.coerceIn(0, 100)

        val state: String
        val urgency: String
        val trigger: String

        if (score >= 80 && flagScreen in listOf("NONE", "LOW") && flagFatigue == "LOW" && flagSwitching in listOf("NONE", "LOW")) {
            state = "OPTIMAL"
            urgency = "LOW"
            trigger = "SUSTAINED_OPTIMAL_FLOW"
        } else if (score >= 60 && flagScreen != "CRITICAL" && flagSwitching != "HIGH") {
            state = "NORMAL"
            urgency = "LOW"
            trigger = "NORMAL_PACING"
        } else if (score >= 35 || flagScreen == "HIGH" || flagSwitching == "HIGH" || flagFatigue == "HIGH") {
            state = "AT_RISK"
            urgency = if (score < 45 || flagScreen == "HIGH") "HIGH" else "MEDIUM"
            trigger = when {
                flagSwitching == "HIGH" -> "RAPID_CONTEXT_SWITCHING"
                flagScreen in listOf("HIGH", "CRITICAL") -> "EXCESSIVE_SCREEN_TIME"
                flagFatigue == "HIGH" -> "HIGH_FATIGUE_STRAIN"
                flagContext == "VULNERABLE_SUBOPTIMAL" -> "VULNERABLE_TASK_CONTEXT"
                flagWindow in listOf("WEAKEST", "OFF_PEAK") -> "OFF_PEAK_FRICTION"
                else -> "PRODUCTIVITY_DROP"
            }
        } else {
            state = "RECOVERY"
            urgency = if (flagScreen == "CRITICAL" || score < 25) "CRITICAL" else "HIGH"
            trigger = when {
                flagScreen == "CRITICAL" -> "EXCESSIVE_SCREEN_TIME"
                flagFatigue == "HIGH" -> "HIGH_FATIGUE_STRAIN"
                flagSwitching == "HIGH" -> "RAPID_CONTEXT_SWITCHING"
                else -> "SEVERE_COGNITIVE_BURNOUT"
            }
        }

        // 7. Deterministic Fallback Coaching Message
        val fallbackMessage = when (state) {
            "RECOVERY" -> when (trigger) {
                "EXCESSIVE_SCREEN_TIME" -> "Immediate recovery needed: You have been on-screen for $screenDurationMin minutes. Step away from all screens for a 15-minute physical reset."
                "HIGH_FATIGUE_STRAIN" -> "Severe fatigue detected ($fatigueScore/100). Step away from $taskType for a 15-minute recovery walk before resuming."
                else -> "Cognitive energy depleted (score: $score/100). Stop active tasks and take an immediate 15-minute recovery break."
            }
            "AT_RISK" -> when (trigger) {
                "RAPID_CONTEXT_SWITCHING" -> "Take a 10-minute break, then start a 25-minute focused session."
                "EXCESSIVE_SCREEN_TIME" -> "Take a 10-minute eye-rest break. Continuous screen time is at $screenDurationMin minutes."
                "VULNERABLE_TASK_CONTEXT" -> "Relocate your $taskType session from $resolvedContext to $bestContext, or shift to a structured planning task."
                "OFF_PEAK_FRICTION" -> "Working outside your peak window. Cap this $taskType block at 25 minutes and reschedule deep work to $bestWindow."
                "HIGH_FATIGUE_STRAIN" -> "Fatigue is rising ($fatigueScore/100). Take a 10-minute recovery break to reset your focus."
                else -> "Focus slipping (score: $score/100). Take a short 5-minute breather and mute non-essential notifications."
            }
            "NORMAL" -> "Pacing is steady (score: $score/100). Continue your current $taskType block in $resolvedContext."
            else -> "Optimal flow state achieved (score: $score/100). Maintain sustained focus in $resolvedContext."
        }

        // 8. Anti-Spam Suppression Rules
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

        // 9. Final Intervention Message
        val intervention = if (isSuppressed) null else fallbackMessage

        // 10. Structured Evidence for Local AI Model
        val structuredEvidence = mapOf<String, Any>(
            "taskType" to taskType,
            "currentHour" to resolvedHour,
            "context" to resolvedContext,
            "screenDurationSeconds" to screenDuration,
            "screenDurationMinutes" to screenDurationMin,
            "recentContextSwitches" to numSwitches,
            "nonProductiveAppCount" to nonProdCount,
            "fatigueScore" to fatigueScore,
            "fatigueLevel" to fatigue.first,
            "isInPeakWindow" to (flagWindow == "PEAK"),
            "bestFocusWindow" to bestWindow,
            "bestContext" to bestContext,
            "facts" to evidence
        )

        val localModelPrompt = "System: You are an on-device personal productivity coach. Generate a 1-sentence supportive coaching intervention.\n" +
            "Context: State=$state, Score=$score/100, Trigger=$trigger, Urgency=$urgency.\n" +
            "Evidence: ${evidence.take(3).joinToString("; ")}.\n" +
            "Coach:"

        return CoachEvaluation(
            state = state,
            score = score,
            trigger = trigger,
            evidence = evidence,
            intervention = intervention,
            urgency = urgency,
            confidence = confidence,
            isInterventionSuppressed = isSuppressed,
            suppressionReason = suppressionReason,
            structuredEvidence = structuredEvidence,
            localModelPrompt = localModelPrompt,
            fallbackMessage = fallbackMessage
        )
    }
}

fun evaluateCurrentState(
    tasks: List<Task>,
    contextSignals: List<ContextSignal> = emptyList(),
    taskType: String = "coding",
    currentHour: Int? = null,
    context: String? = null,
    screenDuration: Long = 0L,
    recentActivity: List<ContextSignal> = emptyList(),
    lastInterventionTime: Long? = null,
    lastTrigger: String? = null,
    currentTime: Long? = null,
    cooldownSeconds: Long = 900L
): CoachEvaluation {
    val engine = InsightEngine(tasks, contextSignals)
    return engine.evaluateCurrentState(
        taskType = taskType,
        currentHour = currentHour,
        context = context,
        screenDuration = screenDuration,
        recentActivity = recentActivity,
        lastInterventionTime = lastInterventionTime,
        lastTrigger = lastTrigger,
        currentTime = currentTime,
        cooldownSeconds = cooldownSeconds
    )
}

fun predictTaskReadiness(
    tasks: List<Task>,
    contextSignals: List<ContextSignal> = emptyList(),
    taskType: String = "coding",
    currentHour: Int? = null,
    currentContext: String? = null,
    recentScreenDuration: Long? = null
): TaskPrediction {
    val engine = InsightEngine(tasks, contextSignals)
    return engine.predictTaskReadiness(taskType, currentHour, currentContext, recentScreenDuration)
}

fun updateUserModel(
    previousModel: UserModel?,
    newTask: Task,
    context: ContextSignal? = null,
    predictedScore: Int? = null
): UserModel {
    val prevTasks = previousModel?.tasks ?: emptyList()
    val prevSignals = previousModel?.contextSignals ?: emptyList()
    val prevCalib = previousModel?.predictionCalibration ?: PredictionCalibration()

    // 2. Prediction vs Actual Outcome Tracking
    val predScore: Int? = if (predictedScore != null) {
        predictedScore
    } else if (prevTasks.isNotEmpty()) {
        val prevEngine = InsightEngine(prevTasks, prevSignals)
        val cal = Calendar.getInstance()
        cal.timeInMillis = newTask.createdAt
        val tHour = cal.get(Calendar.HOUR_OF_DAY)
        val tLoc = newTask.location.ifBlank { context?.location ?: "Home Office" }
        val tScreen = context?.screenOnDuration ?: 0L
        val predRes = prevEngine.predictTaskReadiness(newTask.type.name.lowercase(), tHour, tLoc, tScreen)
        predRes.predictedScore
    } else {
        null
    }

    val isCompleted = newTask.completedAt != null
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

    // 3. Update task list and context signals
    val updatedTasks = prevTasks + listOf(newTask)
    val updatedSignals = if (context != null) prevSignals + listOf(context) else prevSignals

    // 4. Recompute profile with recency weighting
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
