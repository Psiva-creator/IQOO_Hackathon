package com.iqoo.productivity.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.iqoo.productivity.model.TaskType

@Composable
fun StartStopScreen(
    onStartTask: (title: String, type: TaskType) -> Unit,
    onStopTask: () -> Unit,
    isRunning: Boolean = false,
    elapsedSeconds: Long = 0L
) {
    var title by remember { mutableStateOf("") }
    var selectedType by remember { mutableStateOf(TaskType.CODING) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = if (isRunning) "Task in Progress" else "Start a New Focus Session",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(modifier = Modifier.height(24.dp))

        if (!isRunning) {
            OutlinedTextField(
                value = title,
                onValueChange = { title = it },
                label = { Text("Task Title") },
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Task Type Selector Dropdown / Chips can be rendered here
            Text(text = "Selected Category: ${selectedType.name}", style = MaterialTheme.typography.bodyMedium)

            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = { onStartTask(title.ifBlank { "Untitled Task" }, selectedType) },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Start Focus Timer")
            }
        } else {
            val minutes = elapsedSeconds / 60
            val seconds = elapsedSeconds % 60
            Text(
                text = String.format("%02d:%02d", minutes, seconds),
                style = MaterialTheme.typography.displayLarge
            )

            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = { onStopTask() },
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Complete & Save Task")
            }
        }
    }
}
