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
    )
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
        if (tasks.isEmpty()) {
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
                )
            )
        }

        val peakHour = detectPeakHour()
        val procrastinationTrigger = detectProcrastinationTrigger()
        val contextInsights = analyzeContexts()
        val bestContextStr = formatBestContext(contextInsights)
        val fatigue = detectFatigue()
        val distraction = detectDistractionSensitivity()
        val score = calculateProductivityScore()
        val confidence = calculateConfidence()
        val heatmap = generateHourlyHeatmap()
        val recommendation = generateSmartRecommendation(peakHour, contextInsights, fatigue, distraction)

        return InsightResult(
            peakHour = peakHour,
            procrastinationTrigger = procrastinationTrigger,
            bestContext = bestContextStr,
            recommendation = recommendation,
            productivityScore = score,
            confidenceLevel = confidence,
            hourlyHeatmap = heatmap,
            fatigueLevel = fatigue.first,
            fatigueScore = fatigue.second,
            explanation = fatigue.third,
            contextInsights = contextInsights,
            distractionSensitivity = distraction
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
            "Low completion on unplanned afternoon sessions"
        }
    }

    private fun analyzeContexts(): List<ContextInsight> {
        val contextMap = mutableMapOf<String, Triple<Int, Int, MutableList<Long>>>() // loc -> (total, completed, durations)
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

    private fun detectFatigue(): Triple<String, Int, String> { // Level, Score, Explanation
        // 1. Screen-On Duration Strain (0-30 pts)
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

        // 2. Declining Completion Rate: Morning vs Afternoon (0-30 pts)
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

        // 3. Session Duration Degradation (0-20 pts)
        var durationShrinkPts = 0
        var mDur = 0.0
        var aDur = 0.0
        if (morningTasks.isNotEmpty() && afternoonTasks.isNotEmpty()) {
            mDur = morningTasks.map { it.duration }.average()
            aDur = afternoonTasks.map { it.duration }.average()
            if (mDur > 0 && (aDur / mDur) <= 0.50) durationShrinkPts = 20
            else if (mDur > 0 && (aDur / mDur) <= 0.75) durationShrinkPts = 10
        }

        // 4. Context/Task Switching & Distraction Intrusion (0-20 pts)
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
        val typeFailures = mutableMapOf<TaskType, Pair<Int, Int>>() // type -> (total, failed)
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

    private fun generateSmartRecommendation(
        peakHour: String,
        contextInsights: List<ContextInsight>,
        fatigue: Triple<String, Int, String>,
        distraction: DistractionSensitivity
    ): String {
        val priorityRank = mapOf(
            TaskType.CODING to 0,
            TaskType.WRITING to 1,
            TaskType.PLANNING to 2,
            TaskType.READING to 3,
            TaskType.MEETING to 4,
            TaskType.EXERCISE to 5,
            TaskType.OTHER to 6
        )

        val typeRates = mutableMapOf<TaskType, Pair<Int, Int>>()
        for (task in tasks) {
            val curr = typeRates.getOrPut(task.type) { Pair(0, 0) }
            val compInc = if (task.completedAt != null) 1 else 0
            typeRates[task.type] = Pair(curr.first + 1, curr.second + compInc)
        }

        var bestType = TaskType.CODING
        var bestTypeRate = -1
        for ((type, stats) in typeRates) {
            if (stats.first >= 2) {
                val r = ((stats.second.toDouble() / stats.first) * 100).toInt()
                if (r > bestTypeRate || (r == bestTypeRate && (priorityRank[type] ?: 99) < (priorityRank[bestType] ?: 99))) {
                    bestTypeRate = r
                    bestType = type
                }
            }
        }

        val bestCtx = contextInsights.firstOrNull() ?: ContextInsight("Home Office", 85.0, 5, 4, 1800.0, "Optimal")
        val worstCtx = if (contextInsights.size > 1) contextInsights.last() else null

        val parts = mutableListOf<String>()
        val peakClean = peakHour.split("(")[0].trim()
        val bestTypeName = bestType.name.lowercase()
        parts.add("Your $bestTypeName completion rate peaks between $peakClean ($bestTypeRate% completion in ${bestCtx.context}).")

        val vulnerableStr = if (distraction.vulnerableCategories.isNotEmpty()) distraction.vulnerableCategories.joinToString(", ") else "complex"
        if (worstCtx != null && worstCtx.completionRate < bestCtx.completionRate) {
            parts.add("In contrast, $vulnerableStr sessions drop to ${worstCtx.completionRate}% completion in ${worstCtx.context}.")
        }

        val fatigueScore = fatigue.second
        if (fatigueScore >= 65) {
            parts.add("High afternoon fatigue (score: $fatigueScore/100) significantly degrades focus after extended screen sessions.")
            val targetTask = if (worstCtx != null) vulnerableStr else bestTypeName
            parts.add("Consider scheduling difficult $targetTask tasks before 11:00 AM in ${bestCtx.context}, and limit continuous screen blocks to 45 minutes.")
        } else if (fatigueScore >= 35) {
            parts.add("Moderate fatigue (score: $fatigueScore/100) sets in during late afternoon. Schedule high-priority deep work in ${bestCtx.context} during your morning peak.")
        } else {
            parts.add("Maintain your consistent cadence by protecting your $peakClean block for high-priority initiatives.")
        }

        return parts.joinToString(" ")
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
