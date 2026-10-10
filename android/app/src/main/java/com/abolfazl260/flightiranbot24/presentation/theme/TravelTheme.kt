package com.abolfazl260.flightiranbot24.presentation.theme

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.unit.dp

/** Shared Advertio-inspired Android tokens. Actual supplied brand assets replace the legacy icon. */
private val TravelColors = lightColorScheme(
    primary = Color(0xFF007F78),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFE0F4F0),
    onPrimaryContainer = Color(0xFF12394F),
    secondary = Color(0xFF12394F),
    onSecondary = Color.White,
    background = Color(0xFFF1F5F8),
    onBackground = Color(0xFF12394F),
    surface = Color.White,
    onSurface = Color(0xFF12394F),
    surfaceVariant = Color(0xFFE8F0F3),
    onSurfaceVariant = Color(0xFF445660),
    outline = Color(0xFFBBCDD2),
)

private val TravelShapes = Shapes(
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(24.dp),
)

@Composable
internal fun TravelTheme(content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        MaterialTheme(colorScheme = TravelColors, shapes = TravelShapes, content = content)
    }
}
