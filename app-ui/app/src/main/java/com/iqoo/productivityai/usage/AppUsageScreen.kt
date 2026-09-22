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
import androidx.compose.runtime.DisposableEffect
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
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import kotlinx.coroutines.launch

@Composable
fun AppUsageScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val coroutineScope = rememberCoroutineScope()
    val phoneManager = remember { PhoneUsageManager(context) }

    var isPermissionGranted by remember { mutableStateOf(phoneManager.hasUsagePermission()) }
    var usageState by remember { mutableStateOf(UnifiedDigitalUsageState()) }
    var selectedCategory by rememberSaveable { mutableStateOf("All") }
    var isLoading by remember { mutableStateOf(false) }

    val categories = listOf("All", "Productivity", "Communication", "Entertainment", "Social", "Utility")

    fun loadData() {
        coroutineScope.launch {
            isLoading = true
            val hasPerm = phoneManager.hasUsagePermission()
            isPermissionGranted = hasPerm
            if (hasPerm) {
                val sessions = phoneManager.getTodayPhoneSessions()
                usageState = UnifiedUsageAggregator.aggregate(
                    phoneSessions = sessions,
                    laptopSessions = emptyList(),
                    syncStatus = SyncStatus.IDLE,
                    lastSyncTimestamp = 0L,
                    laptopHost = "",
                    isPermissionGranted = true,
                    statusMessage = ""
                )
            }
            isLoading = false
        }
    }

    // Auto-reload when user returns from Settings after granting permission
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) loadData()
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    LaunchedEffect(Unit) { loadData() }

    // ── Permission popup (simple dialog style) ──
    if (!isPermissionGranted) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            contentAlignment = Alignment.Center
        ) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 6.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("📱", fontSize = 40.sp)
                    Text(
                        "Screen Time Access",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center
                    )
                    Text(
                        "Allow usage access to view your exact daily app usage.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                    Spacer(Modifier.height(4.dp))
                    Button(
                        onClick = { phoneManager.openUsageSettings() },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("Allow in Settings", fontWeight = FontWeight.Bold)
                    }
                    Button(
                        onClick = onBack,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant,
                            contentColor = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    ) {
                        Text("Not Now")
                    }
                }
            }
        }
        return
    }

    // ── Screen time dashboard ──
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(onClick = onBack, shape = RoundedCornerShape(10.dp)) { Text("← Back") }
            Text("📱 Screen Time", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Button(
                onClick = { loadData() },
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.secondaryContainer,
                    contentColor = MaterialTheme.colorScheme.onSecondaryContainer
                )
            ) { Text(if (isLoading) "..." else "Refresh") }
        }

        Spacer(Modifier.height(14.dp))

        LazyColumn(modifier = Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(12.dp)) {

            // Total card
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
                            "TODAY'S SCREEN TIME",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            usageState.phoneTotalFormatted,
                            style = MaterialTheme.typography.displaySmall,
                            fontWeight = FontWeight.ExtraBold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Text(
                            "${usageState.appBreakdown.size} apps",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.6f)
                        )
                    }
                }
            }

            // Category chips
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

            item {
                Text(
                    "App Breakdown",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            val filtered = if (selectedCategory == "All") usageState.appBreakdown
                           else usageState.appBreakdown.filter { it.category == selectedCategory }

            if (filtered.isEmpty()) {
                item {
                    Text(
                        if (isLoading) "Loading..." else "No apps recorded yet.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                items(filtered, key = { it.appName }) { app ->
                    AppRow(app, usageState.phoneTotalSeconds)
                }
            }

            item { Spacer(Modifier.height(16.dp)) }
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
                    Box(
                        modifier = Modifier.size(10.dp)
                            .clip(androidx.compose.foundation.shape.CircleShape)
                            .background(categoryColor(item.category))
                    )
                    Spacer(Modifier.width(10.dp))
                    Column {
                        Text(item.appName, fontWeight = FontWeight.SemiBold,
                            style = MaterialTheme.typography.bodyMedium)
                        Text(item.category, style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Text(item.formattedTime, fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.bodyMedium)
            }
            Spacer(Modifier.height(6.dp))
            LinearProgressIndicator(
                progress = {
                    if (totalSeconds > 0)
                        (item.durationSeconds.toFloat() / totalSeconds).coerceIn(0f, 1f)
                    else 0f
                },
                modifier = Modifier.fillMaxWidth().height(5.dp).clip(RoundedCornerShape(3.dp)),
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
    val (bg, fg) = when (category) {
        "Productivity"  -> Pair(Color(0xFFDCFCE7), Color(0xFF15803D))
        "Communication" -> Pair(Color(0xFFE0E7FF), Color(0xFF4338CA))
        "Entertainment" -> Pair(Color(0xFFFCE7F3), Color(0xFFBE185D))
        "Social"        -> Pair(Color(0xFFFFEDD5), Color(0xFFC2410C))
        "Utility"       -> Pair(Color(0xFFF3F4F6), Color(0xFF4B5563))
        else            -> Pair(Color(0xFFF1F5F9), Color(0xFF64748B))
    }
    Box(modifier = Modifier.clip(RoundedCornerShape(4.dp)).background(bg)
        .padding(horizontal = 6.dp, vertical = 2.dp)) {
        Text(category, color = fg, fontSize = 11.sp, fontWeight = FontWeight.Medium)
    }
}
