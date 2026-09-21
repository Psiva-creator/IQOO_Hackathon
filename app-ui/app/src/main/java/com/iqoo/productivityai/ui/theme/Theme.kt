package com.iqoo.productivityai.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val ProductivityColorScheme = lightColorScheme(
    primary = FocusBlue,
    onPrimary = Color.White,
    primaryContainer = FocusBlueSoft,
    onPrimaryContainer = FocusNavy,

    secondary = FocusNavy,
    onSecondary = Color.White,

    background = AppBackground,
    onBackground = TextPrimary,

    surface = CardBackground,
    onSurface = TextPrimary,

    surfaceVariant = FocusBlueSoft,
    onSurfaceVariant = TextSecondary,

    error = StopRed,
    onError = Color.White
)

@Composable
fun ProductivityAITheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = ProductivityColorScheme,
        typography = Typography,
        content = content
    )
}