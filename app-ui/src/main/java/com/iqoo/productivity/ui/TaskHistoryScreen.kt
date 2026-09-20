package com.iqoo.productivity.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.iqoo.productivity.model.Task
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun TaskHistoryScreen(
    tasks: List<Task>,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text(
            text = "Task History",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(modifier = Modifier.height(16.dp))

        if (tasks.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize()) {
                Text(text = "No completed tasks yet. Start a session!", style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(tasks) { task ->
                    TaskCard(task = task)
                }
            }
        }
    }
}

@Composable
fun TaskCard(task: Task) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(text = task.title, style = MaterialTheme.typography.titleMedium)
                Badge { Text(task.type.name) }
            }
            Spacer(modifier = Modifier.height(4.dp))
            val dateStr = SimpleDateFormat("MMM dd, yyyy HH:mm", Locale.getDefault()).format(Date(task.createdAt))
            Text(text = "Created: $dateStr", style = MaterialTheme.typography.bodySmall)
            Text(text = "Duration: ${task.duration / 60} min | Location: ${task.location}", style = MaterialTheme.typography.bodySmall)
        }
    }
}
