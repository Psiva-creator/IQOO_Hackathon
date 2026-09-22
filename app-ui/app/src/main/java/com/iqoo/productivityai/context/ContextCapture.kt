package com.iqoo.productivityai.context

import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.os.SystemClock

/**
 * Android Context & Foreground Signal Capture Module (Member C).
 * Bridges on-device system telemetry (UsageStatsManager, screen duration, location)
 * into privacy-safe ContextSignal objects consumed by the Insight Engine.
 */
data class ContextSignal(
    val timestamp: Long = System.currentTimeMillis(),
    val appCategory: String = "Productivity",
    val location: String = "Home Office",
    val screenOnDuration: Long = 0L // in seconds
)

class ContextCapture(
    private val context: Context? = null,
    var currentLocation: String = "Home Office"
) {
    private var screenOnStartTimeMs: Long = SystemClock.elapsedRealtime()

    companion object {
        // App package category classifications
        val CATEGORIES = mapOf(
            "com.android.chrome" to "Productivity",
            "com.github.android" to "Productivity",
            "com.google.android.apps.docs" to "Productivity",
            "com.google.android.apps.sheets" to "Productivity",
            "com.iqoo.productivityai" to "Productivity",
            "org.telegram.messenger" to "Communication",
            "com.whatsapp" to "Communication",
            "com.google.android.gm" to "Communication",
            "com.slack" to "Communication",
            "com.instagram.android" to "Social",
            "com.twitter.android" to "Social",
            "com.facebook.katana" to "Social",
            "com.google.android.youtube" to "Entertainment",
            "com.netflix.mediaclient" to "Entertainment",
            "com.spotify.music" to "Entertainment"
        )

        fun classifyPackage(packageName: String?): String {
            if (packageName.isNullOrBlank()) return "Productivity"
            return CATEGORIES[packageName] ?: when {
                packageName.contains("social", ignoreCase = true) || packageName.contains("instagram", ignoreCase = true) || packageName.contains("twitter", ignoreCase = true) -> "Social"
                packageName.contains("video", ignoreCase = true) || packageName.contains("youtube", ignoreCase = true) || packageName.contains("game", ignoreCase = true) -> "Entertainment"
                packageName.contains("chat", ignoreCase = true) || packageName.contains("message", ignoreCase = true) || packageName.contains("mail", ignoreCase = true) -> "Communication"
                else -> "Productivity"
            }
        }
    }

    /**
     * Captures current on-device context signal.
     */
    fun captureCurrentSignal(overridePackage: String? = null): ContextSignal {
        val now = System.currentTimeMillis()
        val elapsedSec = ((SystemClock.elapsedRealtime() - screenOnStartTimeMs) / 1000L).coerceAtLeast(0L)
        val fgPackage = overridePackage ?: getForegroundPackage()
        val category = classifyPackage(fgPackage)

        return ContextSignal(
            timestamp = now,
            appCategory = category,
            location = currentLocation.ifBlank { "Home Office" },
            screenOnDuration = elapsedSec
        )
    }

    fun resetScreenSession() {
        screenOnStartTimeMs = SystemClock.elapsedRealtime()
    }

    private fun getForegroundPackage(): String? {
        if (context == null) return null
        return try {
            val usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
                ?: return null
            val endTime = System.currentTimeMillis()
            val beginTime = endTime - 10000L // last 10 seconds
            val usageEvents = usageStatsManager.queryEvents(beginTime, endTime)
            var lastEventPackage: String? = null

            val event = UsageEvents.Event()
            while (usageEvents.hasNextEvent()) {
                usageEvents.getNextEvent(event)
                if (event.eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
                    lastEventPackage = event.packageName
                }
            }
            lastEventPackage
        } catch (_: Exception) {
            null
        }
    }

    /**
     * Queries Android UsageStatsManager to aggregate daily foreground time across app categories.
     * Enables the model to inspect daily screen time distribution (Productivity vs Social vs Entertainment).
     */
    fun getDailyAppUsageSummary(): Map<String, Long> {
        if (context == null) return emptyMap()
        return try {
            val usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
                ?: return emptyMap()
            val cal = java.util.Calendar.getInstance().apply {
                set(java.util.Calendar.HOUR_OF_DAY, 0)
                set(java.util.Calendar.MINUTE, 0)
                set(java.util.Calendar.SECOND, 0)
                set(java.util.Calendar.MILLISECOND, 0)
            }
            val startTime = cal.timeInMillis
            val endTime = System.currentTimeMillis()
            val stats = usageStatsManager.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, startTime, endTime)
            val summary = mutableMapOf<String, Long>()
            for (stat in stats) {
                if (stat.totalTimeInForeground > 0) {
                    val cat = classifyPackage(stat.packageName)
                    val seconds = stat.totalTimeInForeground / 1000L
                    summary[cat] = (summary[cat] ?: 0L) + seconds
                }
            }
            summary
        } catch (_: Exception) {
            emptyMap()
        }
    }
}

