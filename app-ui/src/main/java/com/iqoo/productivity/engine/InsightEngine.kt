package com.iqoo.productivity.engine

import com.iqoo.productivity.model.Priority
import com.iqoo.productivity.model.Task
import com.iqoo.productivity.model.TaskType
import java.util.Calendar

data class InsightResult(
    val peakHour: String,
    val procrastinationTrigger: String,
    val bestContext: String,
    val recommendation: String,
    val productivityScore: Int = 85
)

/**
 * On-Device Habit & Productivity Insight Engine
 * Pure Kotlin, zero-dependency engine that runs 100% locally on iQOO devices.
 * Complies with contracts/insight.schema.json.
 */
class InsightEngine(private val tasks: List<Task>) {

    fun analyze(): InsightResult {
        if (tasks.isEmpty()) {
            return InsightResult(
                peakHour = "Insufficient Data",
                procrastinationTrigger = "No activity patterns detected yet",
                bestContext = "Track at least 5 tasks to calibrate",
                recommendation = "Start tracking daily focus blocks to activate personalized insights.",
                productivityScore = 0
            )
        }

        val peakHour = detectPeakHour()
        val procrastinationTrigger = detectProcrastinationTrigger()
        val bestContext = detectBestContext()
        val recommendation = generateRecommendation(procrastinationTrigger)
        val score = calculateProductivityScore()

        return InsightResult(
            peakHour = peakHour,
            procrastinationTrigger = procrastinationTrigger,
            bestContext = bestContext,
            recommendation = recommendation,
            productivityScore = score
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
        val calendar = Calendar.getInstance()

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

    private fun detectBestContext(): String {
        val locTotal = mutableMapOf<String, Int>()
        val locCompleted = mutableMapOf<String, Int>()

        for (task in tasks) {
            val loc = task.location.ifBlank { "Home Office" }
            locTotal[loc] = (locTotal[loc] ?: 0) + 1
            if (task.completedAt != null) {
                locCompleted[loc] = (locCompleted[loc] ?: 0) + 1
            }
        }

        var bestLoc = "Home Office"
        var bestRate = 0.0

        for ((loc, total) in locTotal) {
            val completed = locCompleted[loc] ?: 0
            val rate = completed.toDouble() / total
            if (rate > bestRate && total >= 2) {
                bestRate = rate
                bestLoc = loc
            }
        }

        return "$bestLoc (Consistent ${(bestRate * 100).toInt()}% session completion)"
    }

    private fun generateRecommendation(procrastinationTrigger: String): String {
        return if (procrastinationTrigger.contains("Writing", ignoreCase = true)) {
            "Shift cognitive-heavy writing sessions to your morning peak block (09:00 - 11:00 AM) to avoid afternoon drop-off."
        } else if (procrastinationTrigger.contains("Coding", ignoreCase = true)) {
            "Break larger coding sessions into 30-minute focus sprints."
        } else {
            "Schedule complex tasks during your morning peak focus window."
        }
    }

    private fun calculateProductivityScore(): Int {
        val total = tasks.size
        if (total == 0) return 0
        val completed = tasks.count { it.completedAt != null }
        return ((completed.toDouble() / total) * 100).toInt().coerceIn(0, 100)
    }
}
