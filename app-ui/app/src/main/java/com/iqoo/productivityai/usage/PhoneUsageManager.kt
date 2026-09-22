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
     * Returns an ordered list of intents to open Usage Access settings.
     * Each is tried in order — first one that doesn't throw opens the settings.
     */
    fun getUsageSettingsIntents(): List<Intent> {
        val pkg = context.packageName
        return listOf(
            // Best: Android 10+ opens directly to THIS app's Usage Access toggle
            Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
                data = android.net.Uri.parse("package:$pkg")
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            },
            // Standard: opens the Usage Access list page
            Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            },
            // iQOO/vivo com.android.settings component
            Intent().apply {
                setClassName(
                    "com.android.settings",
                    "com.android.settings.Settings\$UsageAccessSettingsActivity"
                )
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            },
            // iQOO/vivo com.vivo.settings component (some firmware versions)
            Intent().apply {
                setClassName(
                    "com.vivo.settings",
                    "com.vivo.settings.Settings\$UsageAccessSettingsActivity"
                )
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            },
            // Absolute last resort: open general Settings
            Intent(Settings.ACTION_SETTINGS).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
        )
    }

    /**
     * Opens Usage Access settings. Tries each intent in order; moves to next on failure.
     * Does NOT use resolveActivity() — on Android 11+ that always returns null
     * unless <queries> are declared, and even then fails on some OEM builds.
     * Direct startActivity() in try-catch is the only reliable approach.
     */
    fun openUsageSettings() {
        for (intent in getUsageSettingsIntents()) {
            try {
                context.startActivity(intent)
                return   // success — stop here
            } catch (_: Exception) {
                // This intent not supported on this device — try next
            }
        }
    }

    /** Single intent getter kept for backward compatibility. */
    fun getUsageSettingsIntent(): Intent {
        return Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
            data = android.net.Uri.parse("package:${context.packageName}")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
    }

    /**
     * Returns today's exact per-app screen time (foreground usage per app),
     * matching Android Digital Wellbeing exactly.
     *
     * PRIMARY (API 28+): queryAndAggregateUsageStats(startOfDay, now)
     *   → The OS returns a Map<packageName, UsageStats> where totalTimeInForeground
     *     is already perfectly summed for the exact [startOfDay, now] window.
     *   → No UTC-bucket boundary issues, no manual grouping needed.
     *   → This is the same internal call Android Digital Wellbeing uses.
     *
     * FALLBACK (API < 28): INTERVAL_BEST + group-sum per package
     *   → Same window, manual SUM across sub-records per package.
     */
    fun getTodayPhoneSessions(nowMs: Long = System.currentTimeMillis()): List<AppUsageSession> {
        val manager = usageStatsManager ?: return emptyList()
        val startOfDay = getStartOfDayMillis(nowMs)

        // Step 1: Get exact per-app foreground time from OS
        val aggregated = mutableMapOf<String, Long>()    // pkg -> total foreground ms
        val lastUsedByPkg = mutableMapOf<String, Long>() // pkg -> lastTimeUsed

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            // API 28+: queryAndAggregateUsageStats returns one entry per package,
            // totalTimeInForeground summed across the exact window — zero ambiguity.
            try {
                val pm = context.packageManager
                val statsMap = manager.queryAndAggregateUsageStats(startOfDay, nowMs)
                for ((pkg, stat) in statsMap) {
                    if (isSystemPackage(pkg, pm) || pkg == context.packageName) continue
                    if (stat.totalTimeInForeground <= 0L) continue
                    aggregated[pkg] = stat.totalTimeInForeground
                    lastUsedByPkg[pkg] = stat.lastTimeUsed
                }
            } catch (_: Exception) { }
        }

        // Fallback: INTERVAL_BEST + manual group-sum (also used if aggregated is still empty)
        if (aggregated.isEmpty()) {
            try {
                val pm = context.packageManager
                val rawStats = manager.queryUsageStats(
                    UsageStatsManager.INTERVAL_BEST, startOfDay, nowMs
                )
                for (stat in rawStats ?: emptyList()) {
                    val pkg = stat.packageName ?: continue
                    if (isSystemPackage(pkg, pm) || pkg == context.packageName) continue
                    if (stat.totalTimeInForeground <= 0L) continue
                    aggregated[pkg] = (aggregated[pkg] ?: 0L) + stat.totalTimeInForeground
                    val cur = lastUsedByPkg[pkg] ?: 0L
                    if (stat.lastTimeUsed > cur) lastUsedByPkg[pkg] = stat.lastTimeUsed
                }
            } catch (_: Exception) {
                return emptyList()
            }
        }

        if (aggregated.isEmpty()) return emptyList()

        // Step 2: Enrich lastUsed from events for accurate timeline ordering
        // (events never used for duration — only for chronological ordering in UI)
        try {
            val events = manager.queryEvents(startOfDay, nowMs)
            val ev = UsageEvents.Event()
            while (events.hasNextEvent()) {
                events.getNextEvent(ev)
                if (ev.eventType == UsageEvents.Event.ACTIVITY_RESUMED ||
                    ev.eventType == UsageEvents.Event.ACTIVITY_PAUSED) {
                    val pkg = ev.packageName ?: continue
                    val cur = lastUsedByPkg[pkg] ?: 0L
                    if (ev.timeStamp > cur) lastUsedByPkg[pkg] = ev.timeStamp
                }
            }
        } catch (_: Exception) { }

        // Step 3: Build session list sorted by time-used descending (highest first)
        return aggregated
            .filter { (_, ms) -> ms >= MIN_SESSION_SECONDS * 1000L }
            .entries
            .sortedByDescending { it.value }
            .map { (pkg, ms) ->
                val durationSec = ms / 1000L
                val lastUsed = lastUsedByPkg[pkg]
                    ?.takeIf { it in startOfDay..nowMs } ?: nowMs
                createSessionRecord(pkg, lastUsed, durationSec, context.packageManager)
            }
    }

    companion object {
        const val MIN_SESSION_SECONDS = 2L

        // System packages, OEM launchers, and iQOO/vivo background services
        // that must be filtered from user-facing screen time
        val SYSTEM_PACKAGES = setOf(
            // Core Android OS
            "android",
            "com.android.systemui",
            "com.android.launcher",
            "com.android.launcher2",
            "com.android.launcher3",
            "com.android.settings",
            "com.android.phone",
            "com.android.inputmethod.latin",
            "com.google.android.inputmethod.latin",
            // iQOO / vivo launchers & system apps
            "com.bbk.launcher2",                        // iQOO / vivo Launcher
            "com.vivo.upslide",                         // vivo Control Center
            "com.vivo.assistant",                       // Jovi AI
            "com.vivo.aiassist",
            "com.vivo.daemon",
            "com.vivo.fingerprint",
            "com.vivo.gallery",
            "com.vivo.smartshot",
            "com.vivo.globalImsService",
            "com.vivo.incallui",
            "com.vivo.faceid",
            "com.iqoo.secure",
            "com.iqoo.engineermode",
            "com.vivo.vivomoji",
            "com.vivo.pokenotification",
            "com.vivo.systemmanager",                   // iQOO i-Manager
            "com.bbk.theme",                            // vivo Theme Store
            // Google system services (not user apps)
            "com.google.android.apps.nexuslauncher",
            "com.google.android.gms",
            "com.google.android.gsf",
            "com.google.android.packageinstaller",
            "com.google.android.permissioncontroller",
            "com.google.android.ext.services",
            "com.google.android.ext.shared",
            // Samsung
            "com.sec.android.app.launcher",
            "com.samsung.android.app.telephonyui",
            "com.samsung.android.honeyboard",
            "com.samsung.android.app.cocktailbarservice",
            // Xiaomi/MIUI
            "com.miui.home",
            "com.miui.systemAdSolution",
            // Huawei
            "com.huawei.android.launcher",
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

        fun isSystemPackage(packageName: String, packageManager: PackageManager? = null): Boolean {
            // Explicit known system packages
            if (SYSTEM_PACKAGES.contains(packageName)) return true

            // Filter known OEM system namespaces (NOT com.android.* — Chrome, Play Store etc. live there)
            val lc = packageName.lowercase(Locale.ROOT)
            if (lc.startsWith("com.vivo.") || lc.startsWith("com.iqoo.") ||
                lc.startsWith("com.bbk.") ||
                lc.startsWith("com.qualcomm.") || lc.startsWith("com.qti.") ||
                lc.startsWith("com.google.android.gms")) return true

            // Use FLAG_SYSTEM as final arbiter — catches any unlisted OEM service
            if (packageManager != null) {
                return try {
                    val ai = packageManager.getApplicationInfo(packageName, 0)
                    (ai.flags and ApplicationInfo.FLAG_SYSTEM) != 0
                } catch (_: Exception) { false }
            }
            return false
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
