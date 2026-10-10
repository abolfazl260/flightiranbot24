package com.abolfazl260.flightiranbot24.presentation.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.abolfazl260.flightiranbot24.R

/**
 * Android-only Persian RTL design system. Colors are sourced from resources shared
 * with the remaining Java/XML checklist, not from a separate Compose palette.
 * Typography uses Android's licensed system Persian fallback; no guessed brand font.
 */
internal object TravelTokens {
    val spacingXs = 4.dp
    val spacingSm = 8.dp
    val spacingMd = 12.dp
    val spacingLg = 16.dp
    val spacingXl = 20.dp
    val touchTarget = 48.dp
    val cardRadius = 18.dp
}

private val TravelShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(TravelTokens.cardRadius),
    large = RoundedCornerShape(24.dp),
)

private val defaultTypography = Typography()
private val TravelTypography = Typography(
    headlineSmall = defaultTypography.headlineSmall.copy(
        fontFamily = FontFamily.SansSerif, lineHeight = 36.sp,
    ),
    titleLarge = defaultTypography.titleLarge.copy(
        fontFamily = FontFamily.SansSerif, lineHeight = 32.sp,
    ),
    titleMedium = defaultTypography.titleMedium.copy(
        fontFamily = FontFamily.SansSerif, lineHeight = 28.sp,
    ),
    bodyLarge = defaultTypography.bodyLarge.copy(
        fontFamily = FontFamily.SansSerif, lineHeight = 26.sp,
    ),
    bodyMedium = defaultTypography.bodyMedium.copy(
        fontFamily = FontFamily.SansSerif, lineHeight = 24.sp,
    ),
    bodySmall = defaultTypography.bodySmall.copy(
        fontFamily = FontFamily.SansSerif, lineHeight = 20.sp,
    ),
    labelMedium = defaultTypography.labelMedium.copy(
        fontFamily = FontFamily.SansSerif, lineHeight = 20.sp,
    ),
)

@Composable
internal fun TravelTheme(content: @Composable () -> Unit) {
    // A single well-contrasted light palette is used even in system dark mode
    // until a separately verified dark palette is available.
    val colors = lightColorScheme(
        primary = colorResource(R.color.teal),
        onPrimary = colorResource(R.color.white),
        primaryContainer = colorResource(R.color.primary_container),
        onPrimaryContainer = colorResource(R.color.navy),
        secondary = colorResource(R.color.navy),
        onSecondary = colorResource(R.color.white),
        background = colorResource(R.color.pale),
        onBackground = colorResource(R.color.navy),
        surface = colorResource(R.color.white),
        onSurface = colorResource(R.color.navy),
        surfaceVariant = colorResource(R.color.surface_variant),
        onSurfaceVariant = colorResource(R.color.slate),
        outline = colorResource(R.color.outline),
        error = colorResource(R.color.error),
        onError = colorResource(R.color.white),
    )
    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        MaterialTheme(
            colorScheme = colors,
            typography = TravelTypography,
            shapes = TravelShapes,
            content = content,
        )
    }
}
