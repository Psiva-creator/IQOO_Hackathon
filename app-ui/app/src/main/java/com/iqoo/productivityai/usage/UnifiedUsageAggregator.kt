package com.iqoo.productivityai.usage

/**
 * Aggregates and reconciles multi-device screen time telemetry from Phone (UsageStatsManager)
 * and Laptop (office_kit_bridge.py).
 *
 * Rules:
 * 1. Phone and Laptop sessions remain separate discrete records even if executed simultaneously.
 * 2. Deduplicates repeated laptop sync payloads using stable composite keys.
 * 3. Expands session durations if a newer sync payload brings a larger duration for the same session.
 * 4. Calculates independent Phone, Laptop, and Combined digital screen time totals.
 */
object UnifiedUsageAggregator {

    /**
     * Merges a list of existing sessions with incoming sessions, applying deduplication
     * and in-progress session expansion (larger duration replaces smaller for the same session key).
     */
    fun mergeAndDeduplicate(
        existingSessions: List<AppUsageSession>,
        incomingSessions: List<AppUsageSession>
    ): List<AppUsageSession> {
        val map = LinkedHashMap<String, AppUsageSession>()
        for (session in existingSessions) {
            map[session.id] = session
        }
        for (incoming in incomingSessions) {
            val existing = map[incoming.id]
            if (existing == null || incoming.durationSeconds > existing.durationSeconds) {
                map[incoming.id] = incoming
            }
        }
        return map.values.sortedBy { it.timestamp }
    }

    /**
     * Computes the complete UnifiedDigitalUsageState from phone sessions and laptop sessions.
     */
    fun aggregate(
        phoneSessions: List<AppUsageSession>,
        laptopSessions: List<AppUsageSession>,
        syncStatus: SyncStatus,
        lastSyncTimestamp: Long,
        laptopHost: String,
        isPermissionGranted: Boolean = true,
        statusMessage: String = ""
    ): UnifiedDigitalUsageState {
        // Deduplicate laptop sessions if repeated syncs occurred
        val dedupedLaptop = mergeAndDeduplicate(emptyList(), laptopSessions)

        // Ensure distinct devices are never merged into one single session item
        val combinedTimeline = (phoneSessions + dedupedLaptop).sortedBy { it.timestamp }

        val phoneTotalSec = phoneSessions.sumOf { it.durationSeconds }
        val laptopTotalSec = dedupedLaptop.sumOf { it.durationSeconds }
        val combinedTotalSec = phoneTotalSec + laptopTotalSec

        // Category Totals
        val catMap = mutableMapOf<String, Long>()
        for (session in combinedTimeline) {
            catMap[session.appCategory] = (catMap[session.appCategory] ?: 0L) + session.durationSeconds
        }

        // Per-App Usage Breakdown
        val appMap = LinkedHashMap<String, MutableAppUsage>()
        for (session in combinedTimeline) {
            val entry = appMap.getOrPut(session.appName) {
                MutableAppUsage(
                    appName = session.appName,
                    packageName = session.packageName,
                    category = session.appCategory
                )
            }
            if (session.device == DeviceSource.PHONE) {
                entry.phoneSeconds += session.durationSeconds
            } else if (session.device == DeviceSource.LAPTOP) {
                entry.laptopSeconds += session.durationSeconds
            }
        }

        val appBreakdown = appMap.values.map { item ->
            val totalAppSec = item.phoneSeconds + item.laptopSeconds
            val pct = if (combinedTotalSec > 0) {
                ((totalAppSec.toDouble() / combinedTotalSec) * 100).toInt()
            } else 0

            val dev = when {
                item.phoneSeconds > 0 && item.laptopSeconds > 0 -> DeviceSource.COMBINED
                item.phoneSeconds > 0 -> DeviceSource.PHONE
                else -> DeviceSource.LAPTOP
            }

            AppUsageSummaryItem(
                appName = item.appName,
                packageName = item.packageName,
                category = item.category,
                durationSeconds = totalAppSec,
                formattedTime = UsageFormatUtils.formatDuration(totalAppSec),
                percentage = pct,
                device = dev,
                phoneDurationSeconds = item.phoneSeconds,
                laptopDurationSeconds = item.laptopSeconds
            )
        }.sortedByDescending { it.durationSeconds }

        val lastSyncStr = if (lastSyncTimestamp > 0) {
            UsageFormatUtils.formatTimeHHmm(lastSyncTimestamp)
        } else "Never"

        return UnifiedDigitalUsageState(
            phoneTotalSeconds = phoneTotalSec,
            laptopTotalSeconds = laptopTotalSec,
            combinedTotalSeconds = combinedTotalSec,
            phoneTotalFormatted = UsageFormatUtils.formatDuration(phoneTotalSec),
            laptopTotalFormatted = UsageFormatUtils.formatDuration(laptopTotalSec),
            combinedTotalFormatted = UsageFormatUtils.formatDuration(combinedTotalSec),
            categoryTotals = catMap,
            appBreakdown = appBreakdown,
            chronologicalTimeline = combinedTimeline,
            syncStatus = syncStatus,
            lastSyncTimeFormatted = lastSyncStr,
            laptopHost = laptopHost,
            isPermissionGranted = isPermissionGranted,
            statusMessage = statusMessage
        )
    }

    private class MutableAppUsage(
        val appName: String,
        val packageName: String,
        val category: String,
        var phoneSeconds: Long = 0L,
        var laptopSeconds: Long = 0L
    )
}
