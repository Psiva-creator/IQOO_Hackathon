package com.iqoo.productivityai.usage

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

/**
 * Result data holder for laptop synchronization attempts.
 */
data class LaptopSyncResult(
    val status: SyncStatus,
    val sessions: List<AppUsageSession>,
    val totalSeconds: Long,
    val lastSyncTimestamp: Long,
    val errorMessage: String? = null
)

/**
 * Manages HTTP synchronization between the Android phone and the laptop Office Kit Bridge.
 * Features:
 * - 2.0-second network timeouts
 * - Local filesystem caching (laptop_usage_cache.json)
 * - SharedPreferences configuration for host IP and last sync metadata
 * - Safe offline degradation when laptop is disconnected
 */
class LaptopSyncManager(private val context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getLaptopIp(): String {
        return prefs.getString(KEY_LAPTOP_IP, DEFAULT_LAPTOP_IP) ?: DEFAULT_LAPTOP_IP
    }

    fun setLaptopIp(ip: String) {
        prefs.edit().putString(KEY_LAPTOP_IP, ip.trim()).apply()
    }

    fun getLastSyncTimestamp(): Long {
        return prefs.getLong(KEY_LAST_SYNC_TIME, 0L)
    }

    /**
     * Attempts to fetch live laptop app usage from office_kit_bridge.py.
     * If the laptop is unreachable, falls back to the local cached data.
     */
    suspend fun syncWithLaptop(): LaptopSyncResult = withContext(Dispatchers.IO) {
        val ip = getLaptopIp()
        val bridgeUrl = "http://$ip:$PORT/api/sync"

        try {
            val url = URL(bridgeUrl)
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = TIMEOUT_MS
                readTimeout = TIMEOUT_MS
                setRequestProperty("Accept", "application/json")
            }

            val responseCode = conn.responseCode
            if (responseCode == 200) {
                val reader = BufferedReader(InputStreamReader(conn.inputStream))
                val jsonText = reader.use { it.readText() }
                conn.disconnect()

                // Save to local cache file
                saveCacheToFile(jsonText)
                val now = System.currentTimeMillis()
                prefs.edit().putLong(KEY_LAST_SYNC_TIME, now).apply()

                val (sessions, totalSec) = parseLaptopPayload(jsonText)
                LaptopSyncResult(
                    status = SyncStatus.CONNECTED,
                    sessions = sessions,
                    totalSeconds = totalSec,
                    lastSyncTimestamp = now
                )
            } else {
                conn.disconnect()
                fallbackToCache("HTTP $responseCode from laptop bridge")
            }
        } catch (e: Exception) {
            fallbackToCache(e.localizedMessage ?: "Connection timed out")
        }
    }

    /**
     * Reads directly from the local cache file without network calls.
     */
    fun loadCachedLaptopData(): LaptopSyncResult {
        val cacheFile = File(context.filesDir, CACHE_FILE_NAME)
        if (!cacheFile.exists()) {
            return LaptopSyncResult(
                status = SyncStatus.NOT_CONFIGURED,
                sessions = emptyList(),
                totalSeconds = 0L,
                lastSyncTimestamp = 0L,
                errorMessage = "No laptop connected yet"
            )
        }

        return try {
            val cachedJson = cacheFile.readText()
            val (sessions, totalSec) = parseLaptopPayload(cachedJson)
            LaptopSyncResult(
                status = SyncStatus.OFFLINE_USING_CACHE,
                sessions = sessions,
                totalSeconds = totalSec,
                lastSyncTimestamp = getLastSyncTimestamp()
            )
        } catch (e: Exception) {
            LaptopSyncResult(
                status = SyncStatus.NOT_CONFIGURED,
                sessions = emptyList(),
                totalSeconds = 0L,
                lastSyncTimestamp = 0L,
                errorMessage = "Cache corrupt"
            )
        }
    }

    private fun fallbackToCache(errorReason: String): LaptopSyncResult {
        val cacheFile = File(context.filesDir, CACHE_FILE_NAME)
        if (cacheFile.exists()) {
            try {
                val cachedJson = cacheFile.readText()
                val (sessions, totalSec) = parseLaptopPayload(cachedJson)
                return LaptopSyncResult(
                    status = SyncStatus.OFFLINE_USING_CACHE,
                    sessions = sessions,
                    totalSeconds = totalSec,
                    lastSyncTimestamp = getLastSyncTimestamp(),
                    errorMessage = errorReason
                )
            } catch (e: Exception) {
                // Fallthrough to NOT_CONFIGURED
            }
        }

        return LaptopSyncResult(
            status = SyncStatus.NOT_CONFIGURED,
            sessions = emptyList(),
            totalSeconds = 0L,
            lastSyncTimestamp = 0L,
            errorMessage = errorReason
        )
    }

    private fun saveCacheToFile(jsonText: String) {
        try {
            val cacheFile = File(context.filesDir, CACHE_FILE_NAME)
            cacheFile.writeText(jsonText)
        } catch (e: Exception) {
            // Ignore cache write errors
        }
    }

    companion object {
        const val PORT = 8089
        const val TIMEOUT_MS = 2000
        const val PREFS_NAME = "laptop_sync_prefs"
        const val KEY_LAPTOP_IP = "laptop_host_ip"
        const val KEY_LAST_SYNC_TIME = "last_sync_time"
        const val CACHE_FILE_NAME = "laptop_usage_cache.json"
        const val DEFAULT_LAPTOP_IP = "10.0.2.2" // Default for emulator; user configures physical LAN IP

        /**
         * Parses the /api/sync JSON payload into a list of AppUsageSession objects
         * tagged with DeviceSource.LAPTOP.
         */
        fun parseLaptopPayload(jsonString: String): Pair<List<AppUsageSession>, Long> {
            val sessions = mutableListOf<AppUsageSession>()
            var totalSeconds = 0L

            try {
                val root = JSONObject(jsonString)
                val appUsage = root.optJSONObject("appUsage") ?: return Pair(emptyList(), 0L)

                totalSeconds = appUsage.optLong("totalScreenTimeSeconds", 0L)

                val timeline = appUsage.optJSONArray("timeline")
                if (timeline != null) {
                    for (i in 0 until timeline.length()) {
                        val item = timeline.optJSONObject(i) ?: continue
                        val timestamp = item.optLong("timestamp", System.currentTimeMillis())
                        val appName = item.optString("appName", "Unknown App")
                        val pkgName = item.optString("packageName", appName.lowercase().replace(" ", "."))
                        val category = item.optString("category", item.optString("appCategory", "Productivity"))
                        val duration = item.optLong("durationSeconds", 0L)
                        val formattedTime = item.optString("formattedTime", UsageFormatUtils.formatDuration(duration))
                        val timeStr = item.optString("timeStr", UsageFormatUtils.formatTimeHHmm(timestamp))

                        val id = "LAPTOP_${timestamp}_${appName}"
                        sessions.add(
                            AppUsageSession(
                                id = id,
                                timestamp = timestamp,
                                packageName = pkgName,
                                appName = appName,
                                appCategory = category,
                                durationSeconds = duration,
                                formattedTime = formattedTime,
                                timeStr = timeStr,
                                device = DeviceSource.LAPTOP
                            )
                        )
                    }
                }
            } catch (e: Exception) {
                // Return whatever was successfully parsed
            }

            return Pair(sessions, totalSeconds)
        }
    }
}
