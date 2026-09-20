package com.iqoo.productivity.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

data class InsightUiModel(
    val peakHour: String,
    val procrastinationTrigger: String,
    val bestContext: String,
    val recommendation: String
)

@Composable
fun InsightsScreen(
    insight: InsightUiModel?,
    isLoading: Boolean = false,
    onRefresh: () -> Unit = {}
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(text = "AI Habit Insights", style = MaterialTheme.typography.headlineMedium)
            Button(onClick = onRefresh, enabled = !isLoading) {
                Text("Refresh")
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.padding(16.dp))
        } else if (insight == null) {
            Text("Complete tasks to generate on-device habit insights.")
        } else {
            InsightCard(
                title = "⚡ Peak Productivity Window",
                content = insight.peakHour,
                color = MaterialTheme.colorScheme.primaryContainer
            )
            Spacer(modifier = Modifier.height(12.dp))
            InsightCard(
                title = "⚠️ Procrastination Warning",
                content = insight.procrastinationTrigger,
                color = MaterialTheme.colorScheme.errorContainer
            )
            Spacer(modifier = Modifier.height(12.dp))
            InsightCard(
                title = "📍 Optimal Focus Context",
                content = insight.bestContext,
                color = MaterialTheme.colorScheme.secondaryContainer
            )
            Spacer(modifier = Modifier.height(12.dp))
            InsightCard(
                title = "💡 AI Habit Recommendation",
                content = insight.recommendation,
                color = MaterialTheme.colorScheme.tertiaryContainer
            )
        }
    }
}

@Composable
fun InsightCard(title: String, content: String, color: androidx.compose.ui.graphics.Color) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = color)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = title, style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(6.dp))
            Text(text = content, style = MaterialTheme.typography.bodyMedium)
        }
    }
}
