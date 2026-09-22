package com.iqoo.productivityai.usage

import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

/**
 * Phone-only Screen Time dashboard.
 * Reads exact per-app screen time from Android's UsageStatsManager (same source as Digital Wellbeing).
 * Shows a simple "Allow Access" screen when permission is not yet granted.
 */
@Composable
fun AppUsageScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val phoneManager = remember { PhoneUsageManager(context) }

    var isPermissionGranted by remember { mutableStateOf(phoneManager.hasUsagePermission()) }
    var usageState by remember {
        mutableStateOf(
            UnifiedDigitalUsageState(isPermissionGranted = phoneManager.hasUsagePermission())
        )
    }
    var selectedCategory by rememberSaveable { mutableStateOf("All") }

    val categories = listOf("All", "Productivity", "Communication", "Entertainment", "Social", "Utility")

    fun loadData() {
        coroutineScope.launch {
            val hasPerm = phoneManager.hasUsagePermission()
            isPermissionGranted = hasPerm
            if (!hasPerm) return@launch
            val sessions = phoneManager.getTodayPhoneSessions()
            usageState = UnifiedUsageAggregator.aggregate(
                phoneSessions = sessions,
                laptopSessions = emptyList(),
                syncStatus = SyncStatus.IDLE,
                lastSyncTimestamp = 0L,
                laptopHost = "",
                isPermissionGranted = hasPerm,
                statusMessage = ""
            )
        }
    }

    LaunchedEffect(Unit) { loadData() }

    // — Simple full-screen allow prompt if permission not granted —
    if (!isPermissionGranted) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(32.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("📱", fontSize = 56.sp, textAlign = TextAlign.Center)
            Spacer(modifier = Modifier.height(20.dp))
            Text(
                text = "Allow Screen Time Access",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = "Productivity AI needs permission to read your app usage so it can show your real screen time — exactly as Android Digital Wellbeing does.\n\nAll data stays 100% on your phone.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(28.dp))
            Button(
                onClick = { context.startActivity(phoneManager.getUsageSettingsIntent()) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text(
                    text = "Allow in Settings",
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            Button(
                onClick = onBack,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant,
                    contentColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            ) {
                Text("Back")
            }
        }
        return
    }

    // — Main screen time dashboard —
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Header row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(onClick = onBack, shape = RoundedCornerShape(10.dp)) {
                Text("← Back")
            }
            Text(
                text = "📱 Screen Time",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Button(
                onClick = { loadData() },
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondaryContainer,
                    contentColor = MaterialTheme.colorScheme.onSecondaryContainer)
            ) {
                Text("Refresh")
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Hero total card
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "TODAY'S SCREEN TIME",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = usageState.phoneTotalFormatted,
                            style = MaterialTheme.typography.displaySmall,
                            fontWeight = FontWeight.ExtraBold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "${usageState.appBreakdown.size} apps used today",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                        )
                    }
                }
            }

            // Category filter chips
            item {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(categories) { cat ->
                        FilterChip(
                            selected = selectedCategory == cat,
                            onClick = { selectedCategory = cat },
                            label = { Text(cat) }
                        )
                    }
                }
            }

            // App breakdown header
            item {
                Text(
                    text = "App Breakdown",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // App list filtered by category
            val filteredApps = if (selectedCategory == "All") {
                usageState.appBreakdown
            } else {
                usageState.appBreakdown.filter { it.category == selectedCategory }
            }

            if (filteredApps.isEmpty()) {
                item {
                    Text(
                        text = "No apps in this category today.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                items(filteredApps, key = { it.appName }) { app ->
                    AppRow(app, usageState.phoneTotalSeconds)
                }
            }

            item { Spacer(modifier = Modifier.height(16.dp)) }
        }
    }
}

@Composable
fun AppRow(item: AppUsageSummaryItem, totalSeconds: Long) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Category colour dot
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(androidx.compose.foundation.shape.CircleShape)
                            .background(categoryColor(item.category))
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text(
                            text = item.appName,
                            fontWeight = FontWeight.SemiBold,
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Text(
                            text = item.category,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                Text(
                    text = item.formattedTime,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            Spacer(modifier = Modifier.height(6.dp))
            LinearProgressIndicator(
                progress = {
                    if (totalSeconds > 0) (item.durationSeconds.toFloat() / totalSeconds).coerceIn(0f, 1f) else 0f
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(5.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = categoryColor(item.category),
                trackColor = MaterialTheme.colorScheme.surfaceVariant
            )
        }
    }
}

fun categoryColor(category: String): Color = when (category) {
    "Productivity"  -> Color(0xFF10B981)
    "Communication" -> Color(0xFF6366F1)
    "Entertainment" -> Color(0xFFEC4899)
    "Social"        -> Color(0xFFF59E0B)
    "Utility"       -> Color(0xFF64748B)
    else            -> Color(0xFF94A3B8)
}

@Composable
fun CategoryBadge(category: String) {
    val (bgColor, textColor) = when (category) {
        "Productivity"  -> Pair(Color(0xFFDCFCE7), Color(0xFF15803D))
        "Communication" -> Pair(Color(0xFFE0E7FF), Color(0xFF4338CA))
        "Entertainment" -> Pair(Color(0xFFFCE7F3), Color(0xFFBE185D))
        "Social"        -> Pair(Color(0xFFFFEDD5), Color(0xFFC2410C))
        "Utility"       -> Pair(Color(0xFFF3F4F6), Color(0xFF4B5563))
        else            -> Pair(Color(0xFFF1F5F9), Color(0xFF64748B))
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(bgColor)
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(text = category, color = textColor, fontSize = 11.sp, fontWeight = FontWeight.Medium)
    }
}
