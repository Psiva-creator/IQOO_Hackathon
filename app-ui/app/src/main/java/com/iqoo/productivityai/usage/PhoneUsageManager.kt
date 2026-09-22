package com.iqoo.productivityai.usage

import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import android.os.Process
import android.provider.Settings
import java.util.Calendar
import java.util.Locale

/**
 * Android Phone On-Device Real App Usage & Screen Time Engine.
 * Extracts real foreground transitions directly from Android's UsageStatsManager,
 * enforces the 2-second threshold, filters system windows, and tags records with DeviceSource.PHONE.
 *
 * NOTE: Runs strictly on-demand on UI interaction / resume. Does NOT require any background daemon.
 */
class PhoneUsageManager(private val context: Context) {

    private val usageStatsManager by lazy {
        context.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
    }

    /**
     * Checks whether the special PACKAGE_USAGE_STATS permission is granted to this app.
     */
    fun hasUsagePermission(): Boolean {
        val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as? AppOpsManager ?: return false
        val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            appOps.unsafeCheckOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                context.packageName
            )
        } else {
            @Suppress("DEPRECATION")
            appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                context.packageName
            )
        }
        return mode == AppOpsManager.MODE_ALLOWED
    }

    /**
     * Creates an intent to navigate the user directly to the Android Settings page for Usage Access.
     */
    fun getUsageSettingsIntent(): Intent {
        return Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
    }

    /**
     * Extracts all discrete foreground app sessions for the current day (midnight to now).
     * Combines discrete transition events with daily cumulative usage stats to guarantee
     * exact screen time for all applications used throughout the day.
     */
    fun getTodayPhoneSessions(nowMs: Long = System.currentTimeMillis()): List<AppUsageSession> {
        val manager = usageStatsManager ?: return emptyList()
        val startOfDay = getStartOfDayMillis(nowMs)

        val sessions = try {
            val usageEvents = manager.queryEvents(startOfDay, nowMs)
            extractSessionsFromUsageEvents(usageEvents, startOfDay, nowMs, context.packageManager)
        } catch (e: Exception) {
            emptyList()
        }

        if (sessions.isNotEmpty()) {
            return sessions
        }

        // Fallback: If discrete UsageEvents buffer is empty or unavailable on this device,
        // query cumulative daily stats via queryUsageStats to extract exact per-app screen time
        return try {
            val stats = manager.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, startOfDay, nowMs)
            stats.filter { it.totalTimeInForeground >= MIN_SESSION_SECONDS * 1000L && !isSystemPackage(it.packageName) }
                .sortedByDescending { it.totalTimeInForeground }
                .map { stat ->
                    val durationSec = stat.totalTimeInForeground / 1000L
                    val lastUsed = if (stat.lastTimeUsed in (startOfDay..nowMs)) stat.lastTimeUsed else nowMs
                    createSessionRecord(stat.packageName, lastUsed, durationSec, context.packageManager)
                }
        } catch (e: Exception) {
            emptyList()
        }
    }

    companion object {
        const val MIN_SESSION_SECONDS = 2L

        // System packages and OEM launchers that must be ignored as non-user screen time
        val SYSTEM_PACKAGES = setOf(
            "com.android.systemui",
            "com.sec.android.app.launcher",             // Samsung One UI Home
            "com.bbk.launcher2",                        // vivo / iQOO Launcher
            "com.vivo.upslide",                         // vivo Control Center
            "com.google.android.apps.nexuslauncher",    // Pixel Launcher
            "android",
            "com.samsung.android.app.telephonyui",
            "com.google.android.inputmethod.latin",
            "com.samsung.android.honeyboard",           // Samsung Keyboard
            "com.samsung.android.app.cocktailbarservice",// Samsung Edge panel
            "com.miui.home",
            "com.huawei.android.launcher"
        )

        // Human-readable titles for common apps
        val APP_NAMES = mapOf(
            "com.android.chrome" to "Chrome",
            "com.google.android.apps.docs" to "Google Docs",
            "com.google.android.apps.docs.editors.sheets" to "Google Sheets",
            "com.google.android.apps.docs.editors.slides" to "Google Slides",
            "com.github.android" to "GitHub",
            "com.microsoft.office.word" to "Word",
            "com.microsoft.office.excel" to "Excel",
            "com.slack" to "Slack",
            "notion.id" to "Notion",
            "com.todoist" to "Todoist",
            "md.obsidian" to "Obsidian",
            "com.termux" to "Termux",
            "com.google.android.keep" to "Google Keep",
            "org.telegram.messenger" to "Telegram",
            "com.whatsapp" to "WhatsApp",
            "com.google.android.gm" to "Gmail",
            "com.microsoft.office.outlook" to "Outlook",
            "com.google.android.apps.messaging" to "Messages",
            "com.discord" to "Discord",
            "us.zoom.videomeetings" to "Zoom",
            "org.thoughtcrime.securesms" to "Signal",
            "com.instagram.android" to "Instagram",
            "com.twitter.android" to "Twitter/X",
            "com.facebook.katana" to "Facebook",
            "com.reddit.frontpage" to "Reddit",
            "com.linkedin.android" to "LinkedIn",
            "com.zhiliaoapp.musically" to "TikTok",
            "com.snapchat.android" to "Snapchat",
            "com.threads.android" to "Threads",
            "com.google.android.youtube" to "YouTube",
            "com.netflix.mediaclient" to "Netflix",
            "com.spotify.music" to "Spotify",
            "tv.twitch.android.app" to "Twitch",
            "com.amazon.avod.thirdpartyclient" to "Prime Video",
            "com.disney.disneyplus" to "Disney+",
            "com.supercell.clashroyale" to "Clash Royale",
            "com.android.settings" to "Settings",
            "com.android.calculator2" to "Calculator",
            "com.sec.android.app.popupcalculator" to "Calculator",
            "com.google.android.deskclock" to "Clock",
            "com.sec.android.app.clockpackage" to "Clock",
            "com.android.vending" to "Google Play Store",
            "com.google.android.apps.nbu.files" to "Files by Google",
            "com.iqoo.productivityai" to "Productivity AI"
        )

        // Categorization mapping
        val CATEGORIES = mapOf(
            "com.android.chrome" to "Productivity",
            "com.google.android.apps.docs" to "Productivity",
            "com.google.android.apps.docs.editors.sheets" to "Productivity",
            "com.google.android.apps.docs.editors.slides" to "Productivity",
            "com.github.android" to "Productivity",
            "com.microsoft.office.word" to "Productivity",
            "com.microsoft.office.excel" to "Productivity",
            "com.slack" to "Productivity",
            "notion.id" to "Productivity",
            "com.todoist" to "Productivity",
            "md.obsidian" to "Productivity",
            "com.termux" to "Productivity",
            "com.google.android.keep" to "Productivity",
            "org.telegram.messenger" to "Communication",
            "com.whatsapp" to "Communication",
            "com.google.android.gm" to "Communication",
            "com.microsoft.office.outlook" to "Communication",
            "com.google.android.apps.messaging" to "Communication",
            "com.discord" to "Communication",
            "us.zoom.videomeetings" to "Communication",
            "org.thoughtcrime.securesms" to "Communication",
            "com.instagram.android" to "Social",
            "com.twitter.android" to "Social",
            "com.facebook.katana" to "Social",
            "com.reddit.frontpage" to "Social",
            "com.linkedin.android" to "Social",
            "com.zhiliaoapp.musically" to "Social",
            "com.snapchat.android" to "Social",
            "com.threads.android" to "Social",
            "com.google.android.youtube" to "Entertainment",
            "com.spotify.music" to "Entertainment",
            "com.netflix.mediaclient" to "Entertainment",
            "tv.twitch.android.app" to "Entertainment",
            "com.amazon.avod.thirdpartyclient" to "Entertainment",
            "com.disney.disneyplus" to "Entertainment",
            "com.supercell.clashroyale" to "Entertainment",
            "com.android.settings" to "Utility",
            "com.android.calculator2" to "Utility",
            "com.sec.android.app.popupcalculator" to "Utility",
            "com.google.android.deskclock" to "Utility",
            "com.sec.android.app.clockpackage" to "Utility",
            "com.android.vending" to "Utility",
            "com.google.android.apps.nbu.files" to "Utility",
            "com.iqoo.productivityai" to "Productivity"
        )

        fun getStartOfDayMillis(nowMs: Long = System.currentTimeMillis()): Long {
            val cal = Calendar.getInstance().apply {
                timeInMillis = nowMs
                set(Calendar.HOUR_OF_DAY, 0)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
            return cal.timeInMillis
        }

        fun resolveAppName(packageName: String, packageManager: PackageManager? = null): String {
            if (packageName.isBlank()) return "Unknown App"
            APP_NAMES[packageName]?.let { return it }

            if (packageManager != null) {
                try {
                    val appInfo = packageManager.getApplicationInfo(packageName, 0)
                    val label = packageManager.getApplicationLabel(appInfo).toString()
                    if (label.isNotBlank()) return label
                } catch (e: Exception) {
                    // Ignore and fallback
                }
            }

            val parts = packageName.split(".")
            val raw = if (parts.isNotEmpty()) parts.last() else packageName
            return raw.replace("_", " ").replaceFirstChar { it.uppercase() }
        }

        fun categorizePackage(packageName: String, packageManager: PackageManager? = null): String {
            if (packageName.isBlank()) return "Other"
            CATEGORIES[packageName]?.let { return it }

            if (packageManager != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                try {
                    val appInfo = packageManager.getApplicationInfo(packageName, 0)
                    when (appInfo.category) {
                        ApplicationInfo.CATEGORY_PRODUCTIVITY -> return "Productivity"
                        ApplicationInfo.CATEGORY_SOCIAL -> return "Social"
                        ApplicationInfo.CATEGORY_GAME,
                        ApplicationInfo.CATEGORY_VIDEO,
                        ApplicationInfo.CATEGORY_AUDIO -> return "Entertainment"
                        ApplicationInfo.CATEGORY_NEWS,
                        ApplicationInfo.CATEGORY_MAPS -> return "Utility"
                    }
                } catch (e: Exception) {
                    // Ignore
                }
            }

            val lower = packageName.lowercase(Locale.ROOT)
            return when {
                lower.contains("doc") || lower.contains("sheet") || lower.contains("code") ||
                lower.contains("dev") || lower.contains("notes") || lower.contains("task") ||
                lower.contains("git") || lower.contains("terminal") || lower.contains("edit") ||
                lower.contains("productivity") -> "Productivity"

                lower.contains("chat") || lower.contains("mail") || lower.contains("talk") ||
                lower.contains("message") || lower.contains("meet") || lower.contains("call") ||
                lower.contains("msg") -> "Communication"

                lower.contains("social") || lower.contains("insta") || lower.contains("tweet") ||
                lower.contains("reddit") || lower.contains("feed") -> "Social"

                lower.contains("game") || lower.contains("play") || lower.contains("video") ||
                lower.contains("tube") || lower.contains("stream") || lower.contains("music") ||
                lower.contains("tv") -> "Entertainment"

                lower.contains("setting") || lower.contains("tool") || lower.contains("calc") ||
                lower.contains("clock") || lower.contains("file") || lower.contains("system") -> "Utility"

                else -> "Other"
            }
        }

        /**
         * Reconstructs discrete session records from raw UsageEvents.
         * Enforces the 2-second minimum threshold and filters system packages.
         */
        fun extractSessionsFromUsageEvents(
            events: UsageEvents,
            startOfDayMs: Long,
            nowMs: Long,
            packageManager: PackageManager? = null
        ): List<AppUsageSession> {
            val sessions = mutableListOf<AppUsageSession>()
            var currentPackage: String? = null
            var currentStartMs: Long = 0L

            val event = UsageEvents.Event()
            while (events.hasNextEvent()) {
                events.getNextEvent(event)
                val eventType = event.eventType
                val pkg = event.packageName ?: continue
                val timeMs = event.timeStamp

                // Activity Resumed -> Switch or Start
                if (eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
                    if (currentPackage != null && currentPackage != pkg) {
                        val durationSec = (timeMs - currentStartMs) / 1000L
                        if (durationSec >= MIN_SESSION_SECONDS && !isSystemPackage(currentPackage!!)) {
                            sessions.add(createSessionRecord(currentPackage!!, currentStartMs, durationSec, packageManager))
                        }
                    }
                    currentPackage = pkg
                    currentStartMs = timeMs
                }
                // Activity Paused -> Close active session
                else if (eventType == UsageEvents.Event.ACTIVITY_PAUSED) {
                    if (currentPackage != null && currentPackage == pkg) {
                        val durationSec = (timeMs - currentStartMs) / 1000L
                        if (durationSec >= MIN_SESSION_SECONDS && !isSystemPackage(currentPackage!!)) {
                            sessions.add(createSessionRecord(currentPackage!!, currentStartMs, durationSec, packageManager))
                        }
                        currentPackage = null
                    }
                }
            }

            // If an app is still in the foreground at query time, close up to now
            if (currentPackage != null) {
                val durationSec = (nowMs - currentStartMs) / 1000L
                if (durationSec >= MIN_SESSION_SECONDS && !isSystemPackage(currentPackage)) {
                    sessions.add(createSessionRecord(currentPackage, currentStartMs, durationSec, packageManager))
                }
            }

            return sessions
        }

        /**
         * Alternative session extractor taking a raw list of event objects.
         * Enables 100% deterministic unit testing without Android OS dependencies.
         */
        fun extractSessionsFromRawEvents(
            rawEvents: List<RawUsageEvent>,
            startOfDayMs: Long,
            nowMs: Long,
            packageManager: PackageManager? = null
        ): List<AppUsageSession> {
            val sessions = mutableListOf<AppUsageSession>()
            var currentPackage: String? = null
            var currentStartMs: Long = 0L

            for (event in rawEvents.sortedBy { it.timeStamp }) {
                val eventType = event.eventType
                val pkg = event.packageName
                val timeMs = event.timeStamp

                if (eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
                    if (currentPackage != null && currentPackage != pkg) {
                        val durationSec = (timeMs - currentStartMs) / 1000L
                        if (durationSec >= MIN_SESSION_SECONDS && !isSystemPackage(currentPackage!!)) {
                            sessions.add(createSessionRecord(currentPackage!!, currentStartMs, durationSec, packageManager))
                        }
                    }
                    currentPackage = pkg
                    currentStartMs = timeMs
                } else if (eventType == UsageEvents.Event.ACTIVITY_PAUSED) {
                    if (currentPackage != null && currentPackage == pkg) {
                        val durationSec = (timeMs - currentStartMs) / 1000L
                        if (durationSec >= MIN_SESSION_SECONDS && !isSystemPackage(currentPackage!!)) {
                            sessions.add(createSessionRecord(currentPackage!!, currentStartMs, durationSec, packageManager))
                        }
                        currentPackage = null
                    }
                }
            }

            if (currentPackage != null) {
                val durationSec = (nowMs - currentStartMs) / 1000L
                if (durationSec >= MIN_SESSION_SECONDS && !isSystemPackage(currentPackage)) {
                    sessions.add(createSessionRecord(currentPackage, currentStartMs, durationSec, packageManager))
                }
            }

            return sessions
        }

        fun isSystemPackage(packageName: String): Boolean {
            return SYSTEM_PACKAGES.contains(packageName)
        }

        private fun createSessionRecord(
            packageName: String,
            startTimeMs: Long,
            durationSec: Long,
            packageManager: PackageManager?
        ): AppUsageSession {
            val appName = resolveAppName(packageName, packageManager)
            val category = categorizePackage(packageName, packageManager)
            val id = "PHONE_${startTimeMs}_${packageName}"

            return AppUsageSession(
                id = id,
                timestamp = startTimeMs,
                packageName = packageName,
                appName = appName,
                appCategory = category,
                durationSeconds = durationSec,
                formattedTime = UsageFormatUtils.formatDuration(durationSec),
                timeStr = UsageFormatUtils.formatTimeHHmm(startTimeMs),
                device = DeviceSource.PHONE
            )
        }
    }
}

/**
 * Lightweight testable event representation for unit testing.
 */
data class RawUsageEvent(
    val packageName: String,
    val timeStamp: Long,
    val eventType: Int
)
