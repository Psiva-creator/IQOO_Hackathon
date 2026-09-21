package com.iqoo.productivityai

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun InsightsScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "Your Productivity Insights",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )

        Text(
            text = "Small patterns that can improve your next focus session.",
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        InsightCard(
            title = "🌟 Peak Productivity Window",
            value = "09:00 AM – 11:00 AM",
            background = Color(0xFFEAF2FF)
        )
        InsightCard(
            title = "⚠️ Procrastination Pattern",
            value = "Writing tasks are harder after 3:00 PM",
            background = Color(0xFFFFF4E5)
        )
        InsightCard(
            title = "📍 Best Focus Context",
            value = "Home Office",
            background = Color(0xFFECFDF3)
        )
        InsightCard(
            title = "💡 AI Recommendation",
            value = "Schedule important writing tasks during your morning focus time.",
            background = Color(0xFFF3E8FF)
        )
    }
}

@Composable
fun InsightCard(
    title: String,
    value: String,
    background: Color
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = background)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text(text = title, fontWeight = FontWeight.Bold)
            Text(
                text = value,
                modifier = Modifier.padding(top = 8.dp),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}