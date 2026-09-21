package com.iqoo.productivityai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.room.Room
import com.iqoo.productivityai.ui.theme.ProductivityAITheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

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

    var title by rememberSaveable { mutableStateOf("") }
    var taskType by rememberSaveable { mutableStateOf("coding") }
    var menuExpanded by rememberSaveable { mutableStateOf(false) }
    var isRunning by rememberSaveable { mutableStateOf(false) }
    var elapsedSeconds by rememberSaveable { mutableStateOf(0) }
    var startedAt by rememberSaveable { mutableStateOf(0L) }
    var statusMessage by rememberSaveable { mutableStateOf("") }
    var showHistory by rememberSaveable { mutableStateOf(false) }
    var showInsights by rememberSaveable { mutableStateOf(false) }

    val taskTypes = listOf(
        "coding", "writing", "meeting", "reading",
        "planning", "exercise", "other"
    )

    LaunchedEffect(isRunning) {
        while (isRunning) {
            delay(1000)
            elapsedSeconds++
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Productivity AI") })
        }
    ) { paddingValues ->
        if (showHistory) {
            Column(
                modifier = Modifier.padding(paddingValues)
            ) {
                Button(
                    onClick = { showHistory = false },
                    modifier = Modifier
                        .padding(24.dp)
                        .fillMaxWidth()
                ) {
                    Text("Back to Start Task")
                }

                TaskHistory(tasks)
            }
        } else if (showInsights) {
            Column(
                modifier = Modifier.padding(paddingValues)
            ) {
                Button(
                    onClick = { showInsights = false },
                    modifier = Modifier
                        .padding(24.dp)
                        .fillMaxWidth()
                ) {
                    Text("Back to Start Task")
                }

                InsightsScreen()
            }
        } else {
            Column(
                modifier = Modifier
                    .padding(paddingValues)
                    .padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    text = "Start a focus task",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )

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
                        } else {
                            val finishedAt = System.currentTimeMillis()

                            coroutineScope.launch {
                                database.taskDao().insertTask(
                                    Task(
                                        title = title.ifBlank { "Untitled task" },
                                        type = taskType,
                                        createdAt = startedAt,
                                        completedAt = finishedAt,
                                        duration = elapsedSeconds.toLong(),
                                        location = "Home Office",
                                        priority = "medium"
                                    )
                                )
                            }

                            isRunning = false
                            statusMessage = "Task saved successfully."
                            title = ""
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
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

                Button(
                    onClick = { showHistory = true },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("View Task History")
                }
                Button(
                    onClick = { showInsights = true },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("View Insights")
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