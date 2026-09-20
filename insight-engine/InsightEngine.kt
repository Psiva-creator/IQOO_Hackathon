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
    val adaptiveRecommendations: List<AdaptiveRecommendation> = emptyList()
)

/**
 * On-Device Habit & Productivity Insight Engine
 * Pure Kotlin, zero external dependencies, 100% on-device deterministic analytics.
 * Complies strictly with contracts/insight.schema.json.
 */
class InsightEngine(
    private val tasks: List<Task>,
    private val contextSignals: List<ContextSignal> = emptyList()
) {

    fun analyze(): InsightResult {
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
                adaptiveRecommendations = listOf(defaultRec)
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
            adaptiveRecommendations = adaptiveRecs
        )
    }

    private fun detectPeakHour(): String {
        val completedTasks = tasks.filter { it.completedAt != null }
        if (completedTasks.isEmpty()) return "09:00 - 11:00 AM"

        val hourCounts = mutableMapOf<Int, Int>()
        val calendar = Calendar.getInstance()

        for (task in completedTasks) {
            calendar.timeInMillis = task.createdAt
            val hour = calendar.get(Calendar.HOUR_OF_DAY)
            hourCounts[hour] = (hourCounts[hour] ?: 0) + 1
        }

        val peakStart = hourCounts.maxByOrNull { it.value }?.key ?: 9
        val peakEnd = (peakStart + 2) % 24
        return String.format("%02d:00 - %02d:00 (Peak focus completion)", peakStart, peakEnd)
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
        val contextMap = mutableMapOf<String, Triple<Int, Int, MutableList<Long>>>()
        for (task in tasks) {
            val loc = task.location.ifBlank { "Home Office" }
            val existing = contextMap.getOrPut(loc) { Triple(0, 0, mutableListOf()) }
            val completedInc = if (task.completedAt != null) 1 else 0
            existing.third.add(task.duration)
            contextMap[loc] = Triple(existing.first + 1, existing.second + completedInc, existing.third)
        }

        val results = mutableListOf<ContextInsight>()
        for ((loc, stats) in contextMap) {
            val total = stats.first
            val completed = stats.second
            val rate = if (total > 0) Math.round((completed.toDouble() / total) * 1000.0) / 10.0 else 0.0
            val avgDur = if (total > 0) Math.round((stats.third.sum().toDouble() / total) * 10.0) / 10.0 else 0.0
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
        val tasksByType = tasks.groupBy { it.type }
        val results = mutableListOf<TaskTypeAnalysis>()

        for ((type, typeTasks) in tasksByType) {
            val total = typeTasks.size
            val completed = typeTasks.count { it.completedAt != null }
            val failed = total - completed
            val completionRate = if (total > 0) Math.round((completed.toDouble() / total) * 1000.0) / 10.0 else 0.0
            val abandonRate = if (total > 0) Math.round((failed.toDouble() / total) * 1000.0) / 10.0 else 0.0
            val avgDur = if (total > 0) Math.round((typeTasks.map { it.duration }.sum().toDouble() / total) * 10.0) / 10.0 else 0.0
            val prodScore = ((completionRate * 0.7) + Math.min(1.0, avgDur / 3600.0) * 30.0).toInt().coerceIn(0, 100)

            var strongestWindow = "Insufficient data"
            if (total >= 2) {
                val cal = Calendar.getInstance()
                val hourlyAttempts = mutableMapOf<Int, Int>()
                val hourlyCompleted = mutableMapOf<Int, Int>()

                for (t in typeTasks) {
                    cal.timeInMillis = t.createdAt
                    val h = cal.get(Calendar.HOUR_OF_DAY)
                    hourlyAttempts[h] = (hourlyAttempts[h] ?: 0) + 1
                    if (t.completedAt != null) {
                        hourlyCompleted[h] = (hourlyCompleted[h] ?: 0) + 1
                    }
                }

                var bestHour: Int? = null
                var bestHourRate = -1.0
                for (h in 0 until 24) {
                    val attInWindow = (hourlyAttempts[h] ?: 0) + (hourlyAttempts[(h + 1) % 24] ?: 0)
                    val compInWindow = (hourlyCompleted[h] ?: 0) + (hourlyCompleted[(h + 1) % 24] ?: 0)
                    if (attInWindow > 0 && compInWindow > 0) {
                        val rate = compInWindow.toDouble() / attInWindow
                        if (rate > bestHourRate) {
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
        val bestCtx = contextInsights.firstOrNull()?.context ?: "Home Office"
        val weakestWindow = detectWeakestFocusWindow()
        val peakScore = heatmap.values.maxOrNull() ?: 0
        val completedCount = tasks.count { it.completedAt != null }
        val avgCompletion = if (total > 0) Math.round((completedCount.toDouble() / total) * 1000.0) / 10.0 else 0.0

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
        val completed = tasks.count { it.completedAt != null }
        return ((completed.toDouble() / total) * 100).toInt().coerceIn(0, 100)
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
        val attempts = mutableMapOf<Int, Int>()
        val completed = mutableMapOf<Int, Int>()

        for (task in tasks) {
            calendar.timeInMillis = task.createdAt
            val hour = calendar.get(Calendar.HOUR_OF_DAY)
            attempts[hour] = (attempts[hour] ?: 0) + 1
            if (task.completedAt != null) {
                completed[hour] = (completed[hour] ?: 0) + 1
            }
        }

        return (0..23).associateWith { hour ->
            val att = attempts[hour] ?: 0
            val comp = completed[hour] ?: 0
            if (att == 0) 0 else ((comp.toDouble() / att) * 100).toInt()
        }
    }
}
