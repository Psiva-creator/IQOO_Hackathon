package com.iqoo.productivityai

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun FocusHeader(isRunning: Boolean) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Text(
                text = if (isRunning) "Focus session active" else "Ready for deep work?",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )

            Text(
                text = if (isRunning) {
                    "Stay with this task. Your time is being recorded."
                } else {
                    "Choose a task, start the timer, and build a better work habit."
                },
                modifier = Modifier.padding(top = 8.dp),
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )
        }
    }
}