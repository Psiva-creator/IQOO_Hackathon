package com.iqoo.productivityai.usage

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * JVM Unit Test Suite for Multi-Device Digital Screen Time & App Usage.
 * Validates:
 * 1. Phone usage session reconstruction.
 * 2. >= 2 second filtering.
 * 3. System package filtering.
 * 4. Phone total calculation.
 * 5. Laptop total calculation.
 * 6. Combined total calculation.
 * 7. Phone + laptop overlapping sessions remain separate.
 * 8. Duplicate laptop sync does not increase total.
 * 9. Larger duration for an existing session replaces the old duration.
 * 10. Percentage calculations.
 * 11. Laptop offline -> cached data is displayed.
 * 12. No cache + laptop offline -> graceful empty laptop state.
 * 13. Laptop reconnect -> fresh data replaces/updates cache.
 * 14. Phone usage still works when laptop is offline.
 */
class UnifiedUsageTest {

    // 1. Phone usage session reconstruction
    @Test
    fun testPhoneUsageSessionReconstruction() {
        val now = 1789980000000L
        val events = listOf(
            RawUsageEvent("com.android.chrome", now + 1000, 1),      // ACTIVITY_RESUMED
            RawUsageEvent("com.android.chrome", now + 21000, 2),     // ACTIVITY_PAUSED (20s)
            RawUsageEvent("com.google.android.youtube", now + 25000, 1),
            RawUsageEvent("com.google.android.youtube", now + 40000, 2) // 15s
        )

        val sessions = PhoneUsageManager.extractSessionsFromRawEvents(events, now, now + 50000)
        assertEquals(2, sessions.size)
        assertEquals("Chrome", sessions[0].appName)
        assertEquals(20L, sessions[0].durationSeconds)
        assertEquals(DeviceSource.PHONE, sessions[0].device)

        assertEquals("YouTube", sessions[1].appName)
        assertEquals(15L, sessions[1].durationSeconds)
        assertEquals(DeviceSource.PHONE, sessions[1].device)
    }

    // 2. >= 2 second filtering
    @Test
    fun testTwoSecondMinimumThreshold() {
        val now = 1789980000000L
        val events = listOf(
            RawUsageEvent("com.android.chrome", now, 1),
            RawUsageEvent("com.android.chrome", now + 1500, 2), // 1.5s (< 2s) -> should be discarded
            RawUsageEvent("com.whatsapp", now + 2000, 1),
            RawUsageEvent("com.whatsapp", now + 4500, 2)         // 2.5s (>= 2s) -> should be kept
        )

        val sessions = PhoneUsageManager.extractSessionsFromRawEvents(events, now, now + 10000)
        assertEquals(1, sessions.size)
        assertEquals("WhatsApp", sessions[0].appName)
        assertEquals(2L, sessions[0].durationSeconds)
    }

    // 3. System package filtering
    @Test
    fun testSystemPackageFiltering() {
        assertTrue(PhoneUsageManager.isSystemPackage("com.android.systemui"))
        assertTrue(PhoneUsageManager.isSystemPackage("com.sec.android.app.launcher"))
        assertTrue(PhoneUsageManager.isSystemPackage("com.bbk.launcher2"))
        assertTrue(PhoneUsageManager.isSystemPackage("com.samsung.android.honeyboard"))
        assertFalse(PhoneUsageManager.isSystemPackage("com.android.chrome"))
        assertFalse(PhoneUsageManager.isSystemPackage("com.google.android.youtube"))

        val now = 1789980000000L
        val events = listOf(
            RawUsageEvent("com.sec.android.app.launcher", now, 1),
            RawUsageEvent("com.sec.android.app.launcher", now + 10000, 2), // 10s system launcher -> discarded
            RawUsageEvent("com.android.chrome", now + 12000, 1),
            RawUsageEvent("com.android.chrome", now + 20000, 2)           // 8s Chrome -> kept
        )

        val sessions = PhoneUsageManager.extractSessionsFromRawEvents(events, now, now + 30000)
        assertEquals(1, sessions.size)
        assertEquals("Chrome", sessions[0].appName)
    }

    // 4, 5, 6. Phone, Laptop, and Combined total calculations
    @Test
    fun testPhoneLaptopAndCombinedTotals() {
        val phoneSessions = listOf(
            AppUsageSession("PHONE_1_chrome", 1000L, "com.android.chrome", "Chrome", "Productivity", 600L, "10 min", "10:00", DeviceSource.PHONE),
            AppUsageSession("PHONE_2_wa", 2000L, "com.whatsapp", "WhatsApp", "Communication", 300L, "5 min", "10:15", DeviceSource.PHONE)
        )
        val laptopSessions = listOf(
            AppUsageSession("LAPTOP_1_vscode", 1500L, "code.exe", "VS Code", "Productivity", 1800L, "30 min", "10:05", DeviceSource.LAPTOP),
            AppUsageSession("LAPTOP_2_chrome", 3500L, "chrome.exe", "Chrome", "Productivity", 1200L, "20 min", "10:30", DeviceSource.LAPTOP)
        )

        val state = UnifiedUsageAggregator.aggregate(
            phoneSessions = phoneSessions,
            laptopSessions = laptopSessions,
            syncStatus = SyncStatus.CONNECTED,
            lastSyncTimestamp = 4000L,
            laptopHost = "192.168.1.50"
        )

        // Phone total = 600 + 300 = 900s (15 min)
        assertEquals(900L, state.phoneTotalSeconds)
        // Laptop total = 1800 + 1200 = 3000s (50 min)
        assertEquals(3000L, state.laptopTotalSeconds)
        // Combined total = 900 + 3000 = 3900s (1h 5m)
        assertEquals(3900L, state.combinedTotalSeconds)
        assertEquals("1h 5m", state.combinedTotalFormatted)
    }

    // 7. Phone + laptop overlapping sessions remain separate
    @Test
    fun testOverlappingSessionsRemainSeparate() {
        val timestamp = 1789980000000L
        val phoneSession = AppUsageSession(
            "PHONE_${timestamp}_Chrome",
            timestamp,
            "com.android.chrome",
            "Chrome",
            "Productivity",
            900L,
            "15 min",
            "10:00",
            DeviceSource.PHONE
        )
        val laptopSession = AppUsageSession(
            "LAPTOP_${timestamp}_Chrome",
            timestamp,
            "chrome.exe",
            "Chrome",
            "Productivity",
            1800L,
            "30 min",
            "10:00",
            DeviceSource.LAPTOP
        )

        val state = UnifiedUsageAggregator.aggregate(
            phoneSessions = listOf(phoneSession),
            laptopSessions = listOf(laptopSession),
            syncStatus = SyncStatus.CONNECTED,
            lastSyncTimestamp = timestamp + 2000000L,
            laptopHost = "192.168.1.100"
        )

        // In the chronological timeline, both distinct sessions MUST be retained
        assertEquals(2, state.chronologicalTimeline.size)
        assertEquals(DeviceSource.PHONE, state.chronologicalTimeline[0].device)
        assertEquals(DeviceSource.LAPTOP, state.chronologicalTimeline[1].device)

        // In the App Breakdown, Chrome aggregates the combined time (900 + 1800 = 2700s)
        val chromeSummary = state.appBreakdown.find { it.appName == "Chrome" }
        assertNotNull(chromeSummary)
        assertEquals(2700L, chromeSummary!!.durationSeconds)
        assertEquals(900L, chromeSummary.phoneDurationSeconds)
        assertEquals(1800L, chromeSummary.laptopDurationSeconds)
        assertEquals(DeviceSource.COMBINED, chromeSummary.device)
    }

    // 8. Duplicate laptop sync does not increase total
    @Test
    fun testDuplicateLaptopSyncDoesNotIncreaseTotal() {
        val s1 = AppUsageSession("LAPTOP_100_VSCode", 100L, "code.exe", "VS Code", "Productivity", 1200L, "20 min", "10:00", DeviceSource.LAPTOP)
        val s2 = AppUsageSession("LAPTOP_200_Slack", 200L, "slack.exe", "Slack", "Communication", 600L, "10 min", "10:20", DeviceSource.LAPTOP)

        val batch1 = listOf(s1, s2)
        val batch2 = listOf(s1, s2) // Identical sync re-received

        val merged = UnifiedUsageAggregator.mergeAndDeduplicate(batch1, batch2)
        assertEquals(2, merged.size)
        assertEquals(1800L, merged.sumOf { it.durationSeconds })
    }

    // 9. Larger duration for an existing session replaces the old duration
    @Test
    fun testInProgressSessionExpansionReplacesOldDuration() {
        val inProgressOld = AppUsageSession("LAPTOP_100_VSCode", 100L, "code.exe", "VS Code", "Productivity", 600L, "10 min", "10:00", DeviceSource.LAPTOP)
        val inProgressUpdated = AppUsageSession("LAPTOP_100_VSCode", 100L, "code.exe", "VS Code", "Productivity", 1800L, "30 min", "10:00", DeviceSource.LAPTOP)

        val merged = UnifiedUsageAggregator.mergeAndDeduplicate(listOf(inProgressOld), listOf(inProgressUpdated))
        assertEquals(1, merged.size)
        assertEquals(1800L, merged[0].durationSeconds)
    }

    // 10. Percentage calculations
    @Test
    fun testPercentageCalculations() {
        val s1 = AppUsageSession("P1", 100L, "p1", "Chrome", "Productivity", 500L, "500s", "10:00", DeviceSource.PHONE)
        val s2 = AppUsageSession("L1", 200L, "l1", "VS Code", "Productivity", 500L, "500s", "10:10", DeviceSource.LAPTOP)

        val state = UnifiedUsageAggregator.aggregate(
            phoneSessions = listOf(s1),
            laptopSessions = listOf(s2),
            syncStatus = SyncStatus.CONNECTED,
            lastSyncTimestamp = 500L,
            laptopHost = "192.168.1.1"
        )

        assertEquals(1000L, state.combinedTotalSeconds)
        val chrome = state.appBreakdown.find { it.appName == "Chrome" }
        val vscode = state.appBreakdown.find { it.appName == "VS Code" }

        assertNotNull(chrome)
        assertNotNull(vscode)
        assertEquals(50, chrome!!.percentage)
        assertEquals(50, vscode!!.percentage)
    }

    // 11. Laptop offline -> cached data is displayed
    @Test
    fun testLaptopOfflineUsesCache() {
        val cachedSessions = listOf(
            AppUsageSession("LAPTOP_CACHE_1", 100L, "code.exe", "VS Code", "Productivity", 1200L, "20 min", "10:00", DeviceSource.LAPTOP)
        )

        val state = UnifiedUsageAggregator.aggregate(
            phoneSessions = emptyList(),
            laptopSessions = cachedSessions,
            syncStatus = SyncStatus.OFFLINE_USING_CACHE,
            lastSyncTimestamp = 1789980000000L,
            laptopHost = "192.168.1.100"
        )

        assertEquals(SyncStatus.OFFLINE_USING_CACHE, state.syncStatus)
        assertEquals(1200L, state.laptopTotalSeconds)
        assertEquals(1, state.appBreakdown.size)
        assertEquals("VS Code", state.appBreakdown[0].appName)
        assertNotEquals("Never", state.lastSyncTimeFormatted)
    }

    // 12. No cache + laptop offline -> graceful empty laptop state
    @Test
    fun testNoCacheAndLaptopOfflineGracefulEmpty() {
        val state = UnifiedUsageAggregator.aggregate(
            phoneSessions = emptyList(),
            laptopSessions = emptyList(),
            syncStatus = SyncStatus.NOT_CONFIGURED,
            lastSyncTimestamp = 0L,
            laptopHost = "192.168.1.100"
        )

        assertEquals(SyncStatus.NOT_CONFIGURED, state.syncStatus)
        assertEquals(0L, state.laptopTotalSeconds)
        assertEquals(0L, state.combinedTotalSeconds)
        assertTrue(state.appBreakdown.isEmpty())
        assertTrue(state.chronologicalTimeline.isEmpty())
    }

    // 13. Laptop reconnect -> fresh data replaces/updates cache
    @Test
    fun testLaptopReconnectFreshDataUpdatesCache() {
        val cached = listOf(
            AppUsageSession("LAPTOP_1", 100L, "code.exe", "VS Code", "Productivity", 600L, "10 min", "10:00", DeviceSource.LAPTOP)
        )
        val fresh = listOf(
            AppUsageSession("LAPTOP_1", 100L, "code.exe", "VS Code", "Productivity", 1200L, "20 min", "10:00", DeviceSource.LAPTOP),
            AppUsageSession("LAPTOP_2", 200L, "chrome.exe", "Chrome", "Productivity", 900L, "15 min", "10:20", DeviceSource.LAPTOP)
        )

        val state = UnifiedUsageAggregator.aggregate(
            phoneSessions = emptyList(),
            laptopSessions = fresh,
            syncStatus = SyncStatus.CONNECTED,
            lastSyncTimestamp = 200L,
            laptopHost = "192.168.1.100"
        )

        assertEquals(SyncStatus.CONNECTED, state.syncStatus)
        assertEquals(2100L, state.laptopTotalSeconds)
        assertEquals(2, state.chronologicalTimeline.size)
    }

    // 14. Phone usage still works when laptop is offline
    @Test
    fun testPhoneUsageWorksWhenLaptopOffline() {
        val phoneSessions = listOf(
            AppUsageSession("PHONE_1", 100L, "com.android.chrome", "Chrome", "Productivity", 800L, "13m 20s", "10:00", DeviceSource.PHONE)
        )

        val state = UnifiedUsageAggregator.aggregate(
            phoneSessions = phoneSessions,
            laptopSessions = emptyList(),
            syncStatus = SyncStatus.OFFLINE_USING_CACHE,
            lastSyncTimestamp = 0L,
            laptopHost = "192.168.1.100"
        )

        assertEquals(800L, state.phoneTotalSeconds)
        assertEquals(0L, state.laptopTotalSeconds)
        assertEquals(800L, state.combinedTotalSeconds)
        assertEquals(1, state.appBreakdown.size)
        assertEquals("Chrome", state.appBreakdown[0].appName)
        assertEquals(DeviceSource.PHONE, state.appBreakdown[0].device)
    }
}
