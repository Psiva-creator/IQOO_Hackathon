package com.iqoo.productivityai.usage

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

/**
 * Jetpack Compose Unified Multi-Device Digital Screen Time & App Usage Dashboard.
 * Displays real Phone usage (UsageStatsManager) + real Laptop usage (Office Kit Bridge).
 */
@Composable
fun AppUsageScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    val phoneManager = remember { PhoneUsageManager(context) }
    val laptopManager = remember { LaptopSyncManager(context) }

    var usageState by remember {
        mutableStateOf(
            UnifiedDigitalUsageState(
                isPermissionGranted = phoneManager.hasUsagePermission(),
                laptopHost = laptopManager.getLaptopIp()
            )
        )
    }

    var selectedFilter by rememberSaveable { mutableStateOf("ALL") }
    var showIpDialog by rememberSaveable { mutableStateOf(false) }
    var tempIpInput by rememberSaveable { mutableStateOf(laptopManager.getLaptopIp()) }
    var isSyncing by rememberSaveable { mutableStateOf(false) }

    // Function to load and refresh usage state
    fun refreshData(triggerNetworkSync: Boolean = false) {
        coroutineScope.launch {
            val hasPerm = phoneManager.hasUsagePermission()
            val phoneSessions = if (hasPerm) phoneManager.getTodayPhoneSessions() else emptyList()

            val laptopResult = if (triggerNetworkSync) {
                isSyncing = true
                val res = laptopManager.syncWithLaptop()
                isSyncing = false
                res
            } else {
                laptopManager.loadCachedLaptopData()
            }

            usageState = UnifiedUsageAggregator.aggregate(
                phoneSessions = phoneSessions,
                laptopSessions = laptopResult.sessions,
                syncStatus = laptopResult.status,
                lastSyncTimestamp = laptopResult.lastSyncTimestamp,
                laptopHost = laptopManager.getLaptopIp(),
                isPermissionGranted = hasPerm,
                statusMessage = laptopResult.errorMessage ?: ""
            )
        }
    }

    // Initial load: read cached laptop data and live phone data
    LaunchedEffect(Unit) {
        refreshData(triggerNetworkSync = false)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Top Back Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(onClick = onBack) {
                Text("Back to Start Task")
            }

            Text(
                text = "📱+💻 Digital Usage",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Permission Banner (if Android Usage Access not granted)
        if (!usageState.isPermissionGranted) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "⚠️ Phone Usage Permission Required",
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onErrorContainer
                    )
                    Text(
                        text = "To display your real on-device screen time and habits, please grant Usage Access in Settings.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        modifier = Modifier.padding(vertical = 6.dp)
                    )
                    Button(
                        onClick = {
                            context.startActivity(phoneManager.getUsageSettingsIntent())
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                    ) {
                        Text("Grant Permission")
                    }
                }
            }
            Spacer(modifier = Modifier.height(12.dp))
        }

        // Laptop Connection & Sync Bar
        ConnectionStatusBar(
            state = usageState,
            isSyncing = isSyncing,
            onConfigureIp = {
                tempIpInput = usageState.laptopHost
                showIpDialog = true
            },
            onSyncNow = {
                refreshData(triggerNetworkSync = true)
            }
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Lazy scrollable content for metrics, breakdowns, and timeline
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Hero Total Screen Time Card
            item {
                HeroDigitalUsageCard(usageState)
            }

            // Filter Chips
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = selectedFilter == "ALL",
                        onClick = { selectedFilter = "ALL" },
                        label = { Text("All Devices") }
                    )
                    FilterChip(
                        selected = selectedFilter == "PHONE",
                        onClick = { selectedFilter = "PHONE" },
                        label = { Text("📱 Phone Only") }
                    )
                    FilterChip(
                        selected = selectedFilter == "LAPTOP",
                        onClick = { selectedFilter = "LAPTOP" },
                        label = { Text("💻 Laptop Only") }
                    )
                }
            }

            // Section 1: App Usage Breakdown
            item {
                Text(
                    text = "App Usage Breakdown",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }

            val filteredApps = when (selectedFilter) {
                "PHONE" -> usageState.appBreakdown.filter { it.phoneDurationSeconds > 0 }
                "LAPTOP" -> usageState.appBreakdown.filter { it.laptopDurationSeconds > 0 }
                else -> usageState.appBreakdown
            }

            if (filteredApps.isEmpty()) {
                item {
                    Text(
                        text = "No app usage recorded yet for this view.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                items(filteredApps, key = { "${it.appName}_${it.device}" }) { appItem ->
                    AppBreakdownCard(appItem, selectedFilter)
                }
            }

            // Section 2: Chronological Timeline
            item {
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Chronological Timeline",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    val filteredSessions = when (selectedFilter) {
                        "PHONE" -> usageState.chronologicalTimeline.filter { it.device == DeviceSource.PHONE }
                        "LAPTOP" -> usageState.chronologicalTimeline.filter { it.device == DeviceSource.LAPTOP }
                        else -> usageState.chronologicalTimeline
                    }
                    Text(
                        text = "${filteredSessions.size} sessions",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }

            val filteredSessions = when (selectedFilter) {
                "PHONE" -> usageState.chronologicalTimeline.filter { it.device == DeviceSource.PHONE }
                "LAPTOP" -> usageState.chronologicalTimeline.filter { it.device == DeviceSource.LAPTOP }
                else -> usageState.chronologicalTimeline
            }

            if (filteredSessions.isEmpty()) {
                item {
                    Text(
                        text = "No sessions recorded yet.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                items(filteredSessions, key = { it.id }) { session ->
                    TimelineSessionCard(session)
                }
            }
        }
    }

    // IP Configuration Dialog
    if (showIpDialog) {
        AlertDialog(
            onDismissRequest = { showIpDialog = false },
            title = { Text("Configure Laptop IP") },
            text = {
                Column {
                    Text("Enter the Wi-Fi LAN IP address of your companion laptop running office_kit_bridge.py:")
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = tempIpInput,
                        onValueChange = { tempIpInput = it },
                        label = { Text("Laptop IP Address") },
                        placeholder = { Text("e.g. 192.168.1.100 or 10.0.2.2") },
                        singleLine = true
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        laptopManager.setLaptopIp(tempIpInput)
                        showIpDialog = false
                        refreshData(triggerNetworkSync = true)
                    }
                ) {
                    Text("Save & Sync")
                }
            },
            dismissButton = {
                TextButton(onClick = { showIpDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
fun ConnectionStatusBar(
    state: UnifiedDigitalUsageState,
    isSyncing: Boolean,
    onConfigureIp: () -> Unit,
    onSyncNow: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Row(
            modifier = Modifier
                .padding(horizontal = 14.dp, vertical = 10.dp)
                .fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    val dotColor = when (state.syncStatus) {
                        SyncStatus.CONNECTED -> Color(0xFF10B981)
                        SyncStatus.OFFLINE_USING_CACHE -> Color(0xFFF59E0B)
                        SyncStatus.SYNCING -> Color(0xFF38BDF8)
                        else -> Color(0xFF94A3B8)
                    }
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(dotColor)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    val statusText = when (state.syncStatus) {
                        SyncStatus.CONNECTED -> "Synced with Laptop"
                        SyncStatus.OFFLINE_USING_CACHE -> "Laptop Offline (Cached)"
                        SyncStatus.SYNCING -> "Syncing with Laptop..."
                        SyncStatus.NOT_CONFIGURED -> "Laptop Not Connected Yet"
                        SyncStatus.ERROR -> "Sync Error"
                        SyncStatus.IDLE -> "Laptop Idle"
                    }
                    Text(
                        text = statusText,
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }

                Text(
                    text = "Host: ${state.laptopHost}:8089 | Last: ${state.lastSyncTimeFormatted}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.clickable { onConfigureIp() }
                )
            }

            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                OutlinedButton(
                    onClick = onConfigureIp,
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("IP", fontSize = 12.sp)
                }

                Button(
                    onClick = onSyncNow,
                    enabled = !isSyncing,
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(if (isSyncing) "..." else "Sync", fontSize = 12.sp)
                }
            }
        }
    }
}

@Composable
fun HeroDigitalUsageCard(state: UnifiedDigitalUsageState) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text(
                text = "TODAY'S DIGITAL USAGE",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
            )

            Text(
                text = state.combinedTotalFormatted,
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                // Phone split
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "📱 Phone",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    val phonePct = if (state.combinedTotalSeconds > 0) {
                        ((state.phoneTotalSeconds.toDouble() / state.combinedTotalSeconds) * 100).toInt()
                    } else 0
                    Text(
                        text = "${state.phoneTotalFormatted} ($phonePct%)",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }

                // Laptop split
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "💻 Laptop",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    val laptopPct = if (state.combinedTotalSeconds > 0) {
                        ((state.laptopTotalSeconds.toDouble() / state.combinedTotalSeconds) * 100).toInt()
                    } else 0
                    Text(
                        text = "${state.laptopTotalFormatted} ($laptopPct%)",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
            }
        }
    }
}

@Composable
fun AppBreakdownCard(item: AppUsageSummaryItem, filter: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = item.appName,
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleSmall
                    )
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CategoryBadge(item.category)
                        DeviceBadge(item.device)
                    }
                }

                Column(horizontalAlignment = Alignment.End) {
                    val displayDuration = when (filter) {
                        "PHONE" -> UsageFormatUtils.formatDuration(item.phoneDurationSeconds)
                        "LAPTOP" -> UsageFormatUtils.formatDuration(item.laptopDurationSeconds)
                        else -> item.formattedTime
                    }
                    Text(
                        text = displayDuration,
                        fontWeight = FontWeight.ExtraBold,
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Text(
                        text = "${item.percentage}%",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { (item.percentage / 100f).coerceIn(0f, 1f) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
            )
        }
    }
}

@Composable
fun TimelineSessionCard(session: AppUsageSession) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            modifier = Modifier
                .padding(12.dp)
                .fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = session.timeStr,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                DeviceBadge(session.device)
                Column {
                    Text(
                        text = session.appName,
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.bodyMedium
                    )
                    CategoryBadge(session.appCategory)
                }
            }

            Text(
                text = session.formattedTime,
                fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
fun DeviceBadge(device: DeviceSource) {
    val (bgColor, textColor, label) = when (device) {
        DeviceSource.PHONE -> Triple(Color(0xFFE0F2FE), Color(0xFF0369A1), "📱 Phone")
        DeviceSource.LAPTOP -> Triple(Color(0xFFFEF3C7), Color(0xFFB45309), "💻 Laptop")
        DeviceSource.COMBINED -> Triple(Color(0xFFEDE9FE), Color(0xFF6D28D9), "📱+💻 Dual")
    }

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(bgColor)
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(
            text = label,
            color = textColor,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
fun CategoryBadge(category: String) {
    val (bgColor, textColor) = when (category) {
        "Productivity" -> Pair(Color(0xFFDCFCE7), Color(0xFF15803D))
        "Communication" -> Pair(Color(0xFFE0E7FF), Color(0xFF4338CA))
        "Entertainment" -> Pair(Color(0xFFFCE7F3), Color(0xFFBE185D))
        "Social" -> Pair(Color(0xFFFFEDD5), Color(0xFFC2410C))
        "Utility" -> Pair(Color(0xFFF3F4F6), Color(0xFF4B5563))
        else -> Pair(Color(0xFFF1F5F9), Color(0xFF64748B))
    }

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(bgColor)
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(
            text = category,
            color = textColor,
            fontSize = 11.sp,
            fontWeight = FontWeight.Medium
        )
    }
}
