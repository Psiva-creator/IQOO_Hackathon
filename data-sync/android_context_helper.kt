package com.iqoo.productivity.datasync

import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStats
import android.app.usage.UsageStatsManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import android.os.Process
import android.os.SystemClock
import android.provider.Settings
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

/**
 * Shared Data Contract: ContextSignal
 * Complies strictly with contracts/context_signal.schema.json
 *
 * Example JSON:
 * {
 *   "timestamp": 1789910400000,
 *   "appCategory": "Productivity",
 *   "location": "Home Office",
 *   "screenOnDuration": 2700
 * }
 */
data class ContextSignal(
    val timestamp: Long,
    val appCategory: String,
    val location: String = "Home Office",
    val screenOnDuration: Long = 0L // in seconds
) {
    fun toJson(): String {
        val sanitizedLoc = location.replace("\"", "\\\"")
        val sanitizedCat = appCategory.replace("\"", "\\\"")
        return """{"timestamp":$timestamp,"appCategory":"$sanitizedCat","location":"$sanitizedLoc","screenOnDuration":$screenOnDuration}"""
    }
}

/**
 * Shared Data Contract: AppUsageRecord
 * Tracks individual foreground application sessions with duration.
 */
data class AppUsageRecord(
    val timestamp: Long,
    val packageName: String,
    val appName: String,
    val appCategory: String,
    val durationSeconds: Long
) {
    fun toJson(): String {
        val sanitizedPkg = packageName.replace("\"", "\\\"")
        val sanitizedApp = appName.replace("\"", "\\\"")
        val sanitizedCat = appCategory.replace("\"", "\\\"")
        return """{"timestamp":$timestamp,"packageName":"$sanitizedPkg","appName":"$sanitizedApp","appCategory":"$sanitizedCat","durationSeconds":$durationSeconds}"""
    }
}

/**
 * Android On-Device Foreground Context & App Category Capture
 * Leverages UsageStatsManager and PackageManager for iQOO 15 hardware.
 *
 * Required Permissions:
 * - android.permission.PACKAGE_USAGE_STATS (Special App Access)
 * - android.permission.INTERNET
 * - android.permission.ACCESS_NETWORK_STATE
 */
class UsageStatsContextHelper(private val context: Context) {

    private val usageStatsManager by lazy {
        context.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager
    }

    private val packageCategoryMap = mapOf(
        // Productivity
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

        // Communication
        "org.telegram.messenger" to "Communication",
        "com.whatsapp" to "Communication",
        "com.google.android.gm" to "Communication",
        "com.microsoft.office.outlook" to "Communication",
        "com.google.android.apps.messaging" to "Communication",
        "com.discord" to "Communication",
        "us.zoom.videomeetings" to "Communication",
        "org.thoughtcrime.securesms" to "Communication",

        // Social
        "com.instagram.android" to "Social",
        "com.twitter.android" to "Social",
        "com.facebook.katana" to "Social",
        "com.reddit.frontpage" to "Social",
        "com.linkedin.android" to "Social",
        "com.zhiliaoapp.musically" to "Social",
        "com.snapchat.android" to "Social",
        "com.threads.android" to "Social",

        // Entertainment
        "com.google.android.youtube" to "Entertainment",
        "com.spotify.music" to "Entertainment",
        "com.netflix.mediaclient" to "Entertainment",
        "tv.twitch.android.app" to "Entertainment",
        "com.amazon.avod.thirdpartyclient" to "Entertainment",
        "com.disney.disneyplus" to "Entertainment",
        "com.supercell.clashroyale" to "Entertainment",

        // Utility / System
        "com.android.settings" to "Utility",
        "com.android.calculator2" to "Utility",
        "com.google.android.deskclock" to "Utility",
        "com.android.vending" to "Utility",
        "com.google.android.apps.nbu.files" to "Utility"
    )

    /**
     * Checks whether the special PACKAGE_USAGE_STATS permission is granted.
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
     * Creates an intent to prompt the user to enable Usage Access in Android Settings.
     */
    fun getUsageSettingsIntent(): Intent {
        return Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
    }

    /**
     * Extracts the active foreground package using UsageStatsManager.
     * 1. First attempts queryEvents() in a 10s window for ACTIVITY_RESUMED events.
     * 2. If no event (e.g. user stayed within app without switching), queries recent UsageStats.
     * 3. Falls back smoothly if permissions are missing or unavailable.
     */
    fun getForegroundPackageName(): String {
        val manager = usageStatsManager ?: return DEFAULT_FALLBACK_PACKAGE
        val now = System.currentTimeMillis()

        // 1. Primary: Query recent usage events (high temporal accuracy)
        try {
            val events = manager.queryEvents(now - 10000, now)
            var lastResumedPackage: String? = null
            val event = UsageEvents.Event()

            while (events.hasNextEvent()) {
                events.getNextEvent(event)
                if (event.eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
                    lastResumedPackage = event.packageName
                }
            }
            if (!lastResumedPackage.isNullOrBlank()) {
                return lastResumedPackage
            }
        } catch (e: Exception) {
            // Ignore and fall back to usage stats query
        }

        // 2. Secondary fallback: Query past hour usage stats for most recently active package
        try {
            val statsList: List<UsageStats>? = manager.queryUsageStats(
                UsageStatsManager.INTERVAL_DAILY,
                now - 3600000,
                now
            )
            if (!statsList.isNullOrEmpty()) {
                val mostRecent = statsList.maxByOrNull { it.lastTimeUsed }
                if (mostRecent != null && mostRecent.lastTimeUsed > 0 && !mostRecent.packageName.isNullOrBlank()) {
                    return mostRecent.packageName
                }
            }
        } catch (e: Exception) {
            // Ignore
        }

        return DEFAULT_FALLBACK_PACKAGE
    }

    /**
     * Maps a package name to one of the 6 contract categories:
     * ["Productivity", "Social", "Entertainment", "Communication", "Utility", "Other"]
     */
    fun categorizePackage(packageName: String): String {
        // 1. Exact lookup table
        packageCategoryMap[packageName]?.let { return it }

        // 2. Query Android PackageManager ApplicationInfo.category (API 26+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                val appInfo = context.packageManager.getApplicationInfo(packageName, 0)
                when (appInfo.category) {
                    ApplicationInfo.CATEGORY_PRODUCTIVITY -> return "Productivity"
                    ApplicationInfo.CATEGORY_SOCIAL -> return "Social"
                    ApplicationInfo.CATEGORY_GAME,
                    ApplicationInfo.CATEGORY_VIDEO,
                    ApplicationInfo.CATEGORY_AUDIO -> return "Entertainment"
                    ApplicationInfo.CATEGORY_NEWS,
                    ApplicationInfo.CATEGORY_MAPS -> return "Utility"
                    else -> Unit
                }
            } catch (e: PackageManager.NameNotFoundException) {
                // Ignore
            }
        }

        // 3. Heuristic classification based on package naming patterns
        val lower = packageName.lowercase(Locale.ROOT)
        return when {
            lower.contains("doc") || lower.contains("code") || lower.contains("task") ||
            lower.contains("dev") || lower.contains("note") || lower.contains("sheet") ||
            lower.contains("edit") || lower.contains("git") || lower.contains("terminal") -> "Productivity"

            lower.contains("chat") || lower.contains("mail") || lower.contains("msg") ||
            lower.contains("meet") || lower.contains("call") || lower.contains("talk") -> "Communication"

            lower.contains("social") || lower.contains("insta") || lower.contains("tweet") ||
            lower.contains("feed") || lower.contains("reddit") -> "Social"

            lower.contains("tube") || lower.contains("play") || lower.contains("game") ||
            lower.contains("video") || lower.contains("stream") || lower.contains("music") -> "Entertainment"

            lower.contains("setting") || lower.contains("tool") || lower.contains("calc") ||
            lower.contains("clock") || lower.contains("file") || lower.contains("system") -> "Utility"

            else -> "Other"
        }
    }

    /**
     * Captures an instantaneous ContextSignal conforming to contracts/context_signal.schema.json.
     * Gracefully falls back to "Home Office" if location is null or blank.
     */
    fun captureCurrentSignal(screenOnSeconds: Long, location: String? = null): ContextSignal {
        val pkg = getForegroundPackageName()
        val category = categorizePackage(pkg)
        val validLocation = if (location.isNullOrBlank()) DEFAULT_LOCATION else location.trim()

        return ContextSignal(
            timestamp = System.currentTimeMillis(),
            appCategory = category,
            location = validLocation,
            screenOnDuration = screenOnSeconds.coerceAtLeast(0L)
        )
    }

    companion object {
        const val DEFAULT_FALLBACK_PACKAGE = "com.android.chrome"
        const val DEFAULT_LOCATION = "Home Office"
    }
}

/**
 * BroadcastReceiver monitoring screen-on / screen-off cycles to track continuous focus session duration.
 */
class ScreenSessionTracker(private val context: Context) {
    private var screenOnTimestamp: Long = SystemClock.elapsedRealtime()
    private var isScreenOn: Boolean = true

    private val screenReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                Intent.ACTION_SCREEN_ON,
                Intent.ACTION_USER_PRESENT -> {
                    screenOnTimestamp = SystemClock.elapsedRealtime()
                    isScreenOn = true
                }
                Intent.ACTION_SCREEN_OFF -> {
                    isScreenOn = false
                }
            }
        }
    }

    fun start() {
        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_ON)
            addAction(Intent.ACTION_SCREEN_OFF)
            addAction(Intent.ACTION_USER_PRESENT)
        }
        context.registerReceiver(screenReceiver, filter)
    }

    fun stop() {
        try {
            context.unregisterReceiver(screenReceiver)
        } catch (e: Exception) {
            // Receiver might not be registered
        }
    }

    fun resetSession() {
        screenOnTimestamp = SystemClock.elapsedRealtime()
    }

    fun getContinuousScreenOnSeconds(): Long {
        return if (isScreenOn) {
            ((SystemClock.elapsedRealtime() - screenOnTimestamp) / 1000).coerceAtLeast(0L)
        } else {
            0L
        }
    }
}

/**
 * Dispatches insight data from the iQOO phone to the companion Office Kit Bridge on laptop.
 */
object OfficeKitSyncClient {

    suspend fun dispatchToLaptopBridge(
        insightJson: String,
        laptopHost: String,
        port: Int = 8089
    ): Boolean = withContext(Dispatchers.IO) {
        try {
            val url = URL("http://$laptopHost:$port/api/sync")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                setRequestProperty("Content-Type", "application/json")
                doOutput = true
                connectTimeout = 2500
                readTimeout = 2500
            }

            OutputStreamWriter(conn.outputStream).use { it.write(insightJson) }
            val responseCode = conn.responseCode
            conn.disconnect()
            responseCode == 200
        } catch (e: Exception) {
            false
        }
    }
}
