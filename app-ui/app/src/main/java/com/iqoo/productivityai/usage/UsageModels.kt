package com.iqoo.productivityai.usage

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Device origin identifier for unified multi-device tracking.
 */
enum class DeviceSource {
    PHONE,
    LAPTOP,
    COMBINED
}

/**
 * Connection and synchronization lifecycle state for the Laptop bridge.
 */
enum class SyncStatus {
    IDLE,
    SYNCING,
    CONNECTED,
    OFFLINE_USING_CACHE,
    NOT_CONFIGURED,
    ERROR
}

/**
 * Represents a single discrete foreground session on either Phone or Laptop.
 * Conforms to contracts/app_usage_record.schema.json.
 */
data class AppUsageSession(
    val id: String,                 // Stable composite deduplication key: "${device}_${timestamp}_${appName}"
    val timestamp: Long,            // Epoch millisecond start timestamp
    val packageName: String,        // Package name or executable process name
    val appName: String,            // Human-readable application title
    val appCategory: String,        // Productivity, Social, Entertainment, Communication, Utility, Other
    val durationSeconds: Long,      // Duration in seconds (>= 2s)
    val formattedTime: String,      // e.g. "42 min", "1h 15m", "45s"
    val timeStr: String,            // e.g. "10:15"
    val device: DeviceSource        // PHONE or LAPTOP
)

/**
 * Represents aggregated usage metrics for a specific application.
 */
data class AppUsageSummaryItem(
    val appName: String,
    val packageName: String,
    val category: String,
    val durationSeconds: Long,
    val formattedTime: String,
    val percentage: Int,            // Share (0 - 100) of selected filter or combined total
    val device: DeviceSource,       // PHONE, LAPTOP, or COMBINED
    val phoneDurationSeconds: Long = 0L,
    val laptopDurationSeconds: Long = 0L
)

/**
 * Unified state model passed to the Jetpack Compose UI.
 */
data class UnifiedDigitalUsageState(
    val phoneTotalSeconds: Long = 0L,
    val laptopTotalSeconds: Long = 0L,
    val combinedTotalSeconds: Long = 0L,
    val phoneTotalFormatted: String = "0m",
    val laptopTotalFormatted: String = "0m",
    val combinedTotalFormatted: String = "0m",
    val categoryTotals: Map<String, Long> = emptyMap(),
    val appBreakdown: List<AppUsageSummaryItem> = emptyList(),
    val chronologicalTimeline: List<AppUsageSession> = emptyList(),
    val syncStatus: SyncStatus = SyncStatus.NOT_CONFIGURED,
    val lastSyncTimeFormatted: String = "Never",
    val laptopHost: String = "192.168.1.100",
    val isPermissionGranted: Boolean = true,
    val statusMessage: String = ""
)

/**
 * Utility helper functions for formatting durations and timestamps.
 */
object UsageFormatUtils {

    fun formatDuration(seconds: Long): String {
        val sec = seconds.coerceAtLeast(0L)
        if (sec < 60) return "${sec}s"
        val hours = sec / 3600
        val remainder = sec % 3600
        val minutes = remainder / 60
        val remSec = remainder % 60

        return when {
            hours > 0 && minutes > 0 -> "${hours}h ${minutes}m"
            hours > 0 -> "${hours}h"
            remSec == 0L || minutes >= 10 -> "${minutes} min"
            else -> "${minutes}m ${remSec}s"
        }
    }

    fun formatTimeHHmm(timestampMs: Long): String {
        val sdf = SimpleDateFormat("HH:mm", Locale.getDefault())
        return sdf.format(Date(timestampMs))
    }
}
