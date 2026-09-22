package com.iqoo.productivityai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.room.Room
import com.iqoo.productivityai.ai.LocalAIModelFactory
import com.iqoo.productivityai.context.ContextCapture
import com.iqoo.productivityai.context.ContextSignal
import com.iqoo.productivityai.engine.CoachEvaluation
import com.iqoo.productivityai.engine.InsightEngine
import com.iqoo.productivityai.engine.UserModel
import com.iqoo.productivityai.engine.updateUserModel
import com.iqoo.productivityai.ui.theme.ProductivityAITheme
import com.iqoo.productivityai.usage.AppUsageScreen
import com.iqoo.productivityai.usage.PhoneUsageManager
import androidx.compose.runtime.DisposableEffect
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

enum class ScreenTab(val title: String, val icon: String) {
    FOCUS("Focus", "🎯"),
    INSIGHTS("Insights", "📊"),
    SCREEN_TIME("Screen Time", "📱"),
    HISTORY("History", "📜")
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            ProductivityAITheme {
                ProductivityApp()
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProductivityApp() {
    val context = LocalContext.current
    val database = remember {
        Room.databaseBuilder(
            context.applicationContext,
            AppDatabase::class.java,
            "productivity_database"
        ).build()
    }
    val coroutineScope = rememberCoroutineScope()
    val tasks by database.taskDao().getAllTasks().collectAsState(initial = emptyList())

    val contextCapture = remember { ContextCapture(context) }
    val localModel = remember { LocalAIModelFactory.getModel(context) }

    val phoneManager = remember { PhoneUsageManager(context) }
    var hasUsagePermission by remember { mutableStateOf(phoneManager.hasUsagePermission()) }
    val lifecycleOwner = LocalLifecycleOwner.current

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                hasUsagePermission = phoneManager.hasUsagePermission()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    var userModel by remember { mutableStateOf<UserModel?>(null) }
    var activeCoachEval by remember { mutableStateOf<CoachEvaluation?>(null) }
    var currentTab by rememberSaveable { mutableStateOf(ScreenTab.FOCUS) }

    var title by rememberSaveable { mutableStateOf("") }
    var taskType by rememberSaveable { mutableStateOf("coding") }
    var menuExpanded by rememberSaveable { mutableStateOf(false) }
    var isRunning by rememberSaveable { mutableStateOf(false) }
    var elapsedSeconds by rememberSaveable { mutableStateOf(0) }
    var startedAt by rememberSaveable { mutableStateOf(0L) }
    var statusMessage by rememberSaveable { mutableStateOf("") }

    val taskTypes = listOf(
        "coding", "writing", "meeting", "reading",
        "planning", "exercise", "other"
    )

    // Evaluate coach asynchronously when task starts or task type changes
    LaunchedEffect(taskType, isRunning) {
        if (tasks.isNotEmpty() || userModel != null) {
            val signal = contextCapture.captureCurrentSignal()

            // Feed real today's screen time into the engine
            // getDailyAppUsageSummary() returns per-category seconds from actual phone usage
            val dailyUsage = contextCapture.getDailyAppUsageSummary()
            val totalScreenSec = contextCapture.getTotalScreenTimeSeconds()
                .takeIf { it > 0L } ?: signal.screenOnDuration

            // Build enriched context signals — one signal per category with real duration
            val enrichedSignals = if (dailyUsage.isNotEmpty()) {
                dailyUsage.map { (cat, secs) ->
                    signal.copy(appCategory = cat, screenOnDuration = secs)
                }
            } else {
                listOf(signal)
            }

            val engine = InsightEngine(tasks, enrichedSignals)
            engine.evaluateAndCoachAsync(
                currentTaskType = taskType,
                currentContext = signal.location,
                screenDuration = totalScreenSec,
                model = localModel
            ) { eval ->
                activeCoachEval = eval
            }
        }
    }

    LaunchedEffect(isRunning) {
        while (isRunning) {
            delay(1000)
            elapsedSeconds++
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "Productivity AI",
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.titleLarge
                        )
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = MaterialTheme.colorScheme.primaryContainer
                        ) {
                            Text(
                                text = currentTab.title,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                        }
                    }
                }
            )
        },
        bottomBar = {
            NavigationBar {
                ScreenTab.values().forEach { tab ->
                    NavigationBarItem(
                        selected = currentTab == tab,
                        onClick = { currentTab = tab },
                        icon = { Text(tab.icon, fontSize = 18.sp) },
                        label = { Text(tab.title, style = MaterialTheme.typography.labelSmall) }
                    )
                }
            }
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when (currentTab) {
                ScreenTab.FOCUS -> {
                    val scrollState = rememberScrollState()
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(scrollState)
                            .padding(24.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        // Simple Screen Time Permission Card
                        if (!hasUsagePermission) {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(14.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.primaryContainer
                                )
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(14.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = "📱 Screen Time & AI",
                                            style = MaterialTheme.typography.titleSmall,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.onPrimaryContainer
                                        )
                                        Text(
                                            text = "Allow access to track real app usage & fatigue",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                                        )
                                    }
                                    Spacer(Modifier.width(8.dp))
                                    Button(
                                        onClick = { phoneManager.openUsageSettings() },
                                        shape = RoundedCornerShape(10.dp)
                                    ) {
                                        Text("Allow", fontWeight = FontWeight.Bold)
                                    }
                                }
                            }
                        }

                        Text(
                            text = "Start a focus task",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold
                        )
                        FocusHeader(isRunning = isRunning)

                        // Real-time AI Coach suggestion if evaluated
                        activeCoachEval?.let { eval ->
                            val tip = eval.intervention ?: if (eval.state == "AT_RISK" || eval.state == "RECOVERY") eval.fallbackMessage else null
                            if (!tip.isNullOrBlank()) {
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(12.dp),
                                    colors = CardDefaults.cardColors(
                                        containerColor = if (eval.state == "AT_RISK") Color(0xFFFEF2F2) else Color(0xFFF0FDF4)
                                    )
                                ) {
                                    Row(
                                        modifier = Modifier.padding(12.dp),
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                                    ) {
                                        Text(
                                            text = if (eval.state == "AT_RISK") "⚠️" else "💡",
                                            fontSize = 18.sp
                                        )
                                        Column(modifier = Modifier.weight(1f)) {
                                            Text(
                                                text = "Coach: $tip",
                                                style = MaterialTheme.typography.bodySmall,
                                                fontWeight = FontWeight.Medium,
                                                color = MaterialTheme.colorScheme.onSurface
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        // Unified Quick Context Card (Phone Screen Time + Optimal Context)
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { currentTab = ScreenTab.SCREEN_TIME },
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant
                            )
                        ) {
                            Row(
                                modifier = Modifier.padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                    Text(
                                        text = "📱 Screen Time",
                                        style = MaterialTheme.typography.labelMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    Text(
                                        text = "Tap to view today's app usage",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.outline
                                    )
                                }
                                Text("→", fontWeight = FontWeight.Bold)
                            }
                        }

                        OutlinedTextField(
                            value = title,
                            onValueChange = { title = it },
                            label = { Text("Task title") },
                            modifier = Modifier.fillMaxWidth()
                        )

                        ExposedDropdownMenuBox(
                            expanded = menuExpanded,
                            onExpandedChange = { menuExpanded = !menuExpanded }
                        ) {
                            OutlinedTextField(
                                value = taskType.replaceFirstChar { it.uppercase() },
                                onValueChange = {},
                                readOnly = true,
                                label = { Text("Task type") },
                                trailingIcon = {
                                    ExposedDropdownMenuDefaults.TrailingIcon(menuExpanded)
                                },
                                modifier = Modifier
                                    .menuAnchor()
                                    .fillMaxWidth()
                            )

                            ExposedDropdownMenu(
                                expanded = menuExpanded,
                                onDismissRequest = { menuExpanded = false }
                            ) {
                                taskTypes.forEach { type ->
                                    DropdownMenuItem(
                                        text = {
                                            Text(type.replaceFirstChar { it.uppercase() })
                                        },
                                        onClick = {
                                            taskType = type
                                            menuExpanded = false
                                        }
                                    )
                                }
                            }
                        }

                        if (isRunning) {
                            Text(
                                text = "Focus time: ${formatDuration(elapsedSeconds)}",
                                style = MaterialTheme.typography.headlineMedium
                            )
                        }

                        Button(
                            onClick = {
                                if (!isRunning) {
                                    elapsedSeconds = 0
                                    startedAt = System.currentTimeMillis()
                                    statusMessage = ""
                                    isRunning = true
                                    contextCapture.resetScreenSession()
                                } else {
                                    val finishedAt = System.currentTimeMillis()
                                    val currentSignal = contextCapture.captureCurrentSignal()

                                    val newTask = Task(
                                        title = title.ifBlank { "Untitled task" },
                                        type = taskType,
                                        createdAt = startedAt,
                                        completedAt = finishedAt,
                                        duration = elapsedSeconds.toLong(),
                                        location = currentSignal.location,
                                        priority = "medium"
                                    )

                                    coroutineScope.launch {
                                        database.taskDao().insertTask(newTask)
                                        // Closed learning loop: update habit model with completed outcome
                                        userModel = updateUserModel(
                                            previousModel = userModel,
                                            newTask = newTask,
                                            context = currentSignal
                                        )
                                    }

                                    isRunning = false
                                    statusMessage = "Task saved · Habit model updated."
                                    title = ""
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (isRunning) {
                                    MaterialTheme.colorScheme.error
                                } else {
                                    MaterialTheme.colorScheme.primary
                                }
                            )
                        ) {
                            Text(if (isRunning) "Stop Task" else "Start Task")
                        }

                        if (statusMessage.isNotBlank()) {
                            Text(
                                text = statusMessage,
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.Bold
                            )
                        }

                        Spacer(modifier = Modifier.height(8.dp))
                    }
                }

                ScreenTab.INSIGHTS -> {
                    InsightsScreen(
                        tasks = tasks,
                        contextSignals = listOf(contextCapture.captureCurrentSignal())
                    )
                }

                ScreenTab.SCREEN_TIME -> {
                    AppUsageScreen(
                        onBack = { currentTab = ScreenTab.FOCUS }
                    )
                }

                ScreenTab.HISTORY -> {
                    TaskHistory(tasks)
                }
            }
        }
    }
}

fun formatDuration(seconds: Int): String {
    val minutes = seconds / 60
    val remainingSeconds = seconds % 60
    return "%02d:%02d".format(minutes, remainingSeconds)
}