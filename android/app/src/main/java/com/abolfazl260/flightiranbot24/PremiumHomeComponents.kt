package com.abolfazl260.flightiranbot24

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.abolfazl260.flightiranbot24.domain.HomeDestination

// Inspired by the user's visual reference, recreated as scalable first-party
// Jetpack Compose artwork rather than hardcoded screenshot imagery.
private val Midnight = Color(0xFF062D4D)
private val Ocean = Color(0xFF0C557D)
private val Mint = Color(0xFFBFEFE3)
private val SoftMint = Color(0xFFE5F7F2)
private val Ink = Color(0xFF0D2C44)
private val Muted = Color(0xFF5D6D7D)
private val Outline = Color(0xFFE0EAF0)
private val Sky = Color(0xFFDFEFFB)

@Composable
internal fun PremiumHomeHero(onPrices: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(9.dp, RoundedCornerShape(29.dp))
            .clip(RoundedCornerShape(29.dp))
            .background(
                Brush.linearGradient(
                    listOf(Color(0xFF0D527D), Midnight, Color(0xFF02233E)),
                ),
            )
            .height(262.dp),
    ) {
        HeroIllustration()
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 19.dp),
            horizontalAlignment = Alignment.Start,
        ) {
            Text(
                text = stringResource(R.string.hero_eyebrow),
                color = Mint,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(11.dp))
            Text(
                text = stringResource(R.string.welcome_title),
                color = Color.White,
                style = MaterialTheme.typography.headlineSmall,
                fontSize = 26.sp,
                lineHeight = 38.sp,
                fontWeight = FontWeight.ExtraBold,
            )
            Spacer(Modifier.height(7.dp))
            Text(
                text = stringResource(R.string.welcome_description),
                color = Color(0xFFE2EFF8),
                fontSize = 13.sp,
                lineHeight = 23.sp,
                maxLines = 3,
            )
            Spacer(Modifier.weight(1f))
            Button(
                onClick = onPrices,
                shape = RoundedCornerShape(24.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.White,
                    contentColor = Midnight,
                ),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(
                    horizontal = 17.dp, vertical = 12.dp,
                ),
                modifier = Modifier.align(Alignment.Start),
            ) {
                Text(stringResource(R.string.hero_action), fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.width(7.dp))
                Text("←", fontWeight = FontWeight.Bold, fontSize = 18.sp)
            }
        }
    }
}

@Composable
private fun BoxScope.HeroIllustration() {
    Canvas(modifier = Modifier.matchParentSize()) {
        // Layered sky, ambient light and cloud banks on the left side.
        drawCircle(
            brush = Brush.radialGradient(
                listOf(Color(0xFF71B9D8).copy(alpha = 0.42f), Color.Transparent),
            ),
            radius = size.width * 0.70f,
            center = Offset(size.width * 0.07f, size.height * 0.68f),
        )
        val cloud = Color(0xFFDAECF4).copy(alpha = 0.28f)
        drawCircle(cloud, size.width * 0.19f, Offset(size.width * 0.01f, size.height * 0.93f))
        drawCircle(cloud, size.width * 0.12f, Offset(size.width * 0.18f, size.height * 0.91f))
        drawCircle(cloud, size.width * 0.15f, Offset(size.width * 0.31f, size.height * 1.03f))
        drawCircle(Color.White.copy(alpha = 0.08f), size.width * 0.48f,
            Offset(-size.width * 0.30f, -size.height * 0.10f))
        // Hand-drawn top-view airplane. Decorative, not an external image URL.
        withTransform({
            translate(left = size.width * 0.30f, top = size.height * 0.70f)
            rotate(degrees = -21f, pivot = Offset.Zero)
            scale(scaleX = size.width / 360f, scaleY = size.width / 360f, pivot = Offset.Zero)
        }) {
            val wings = Path().apply {
                moveTo(3f, -7f)
                lineTo(-47f, -45f)
                lineTo(-60f, -43f)
                lineTo(-32f, -3f)
                lineTo(-32f, 3f)
                lineTo(-60f, 43f)
                lineTo(-47f, 45f)
                lineTo(3f, 7f)
                close()
            }
            drawPath(wings, Color(0xFFE8F5FF))
            val body = Path().apply {
                moveTo(-78f, -6f)
                cubicTo(-36f, -10f, 44f, -9f, 75f, -5f)
                quadraticTo(91f, 0f, 75f, 5f)
                cubicTo(44f, 9f, -36f, 10f, -78f, 6f)
                close()
            }
            drawPath(body, Color.White)
            val tail = Path().apply {
                moveTo(-63f, -4f)
                lineTo(-80f, -24f)
                lineTo(-88f, -22f)
                lineTo(-82f, 0f)
                lineTo(-88f, 22f)
                lineTo(-80f, 24f)
                lineTo(-63f, 4f)
                close()
            }
            drawPath(tail, Color(0xFFD6EAF8))
            drawLine(Ocean.copy(alpha = 0.7f), Offset(-49f, 0f), Offset(62f, 0f), 1.8f)
        }
    }
}

@Composable
internal fun PremiumPreparationSection(
    onChecklist: () -> Unit,
    onAirportServices: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        PremiumSectionTitle(
            title = stringResource(R.string.home_offline_heading),
            subtitle = stringResource(R.string.premium_prep_subtitle),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            PremiumFeatureCard(
                modifier = Modifier.weight(1f),
                title = stringResource(R.string.checklist_title),
                detail = stringResource(R.string.premium_checklist_description),
                illustration = false,
                badge = null,
                onClick = onChecklist,
            )
            PremiumFeatureCard(
                modifier = Modifier.weight(1f),
                title = stringResource(R.string.offline_airports),
                detail = stringResource(R.string.premium_airport_description),
                illustration = true,
                badge = stringResource(R.string.airports_coming_soon_title),
                onClick = onAirportServices,
            )
        }
    }
}

@Composable
private fun PremiumFeatureCard(
    modifier: Modifier,
    title: String,
    detail: String,
    illustration: Boolean,
    badge: String?,
    onClick: () -> Unit,
) {
    Card(
        onClick = onClick,
        modifier = modifier.semantics { contentDescription = title },
        shape = RoundedCornerShape(24.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Outline),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
    ) {
        Column(modifier = Modifier.fillMaxWidth()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(112.dp)
                    .background(
                        Brush.verticalGradient(
                            if (illustration) listOf(Color(0xFFD5EEFC), Color(0xFFF1F8FF))
                            else listOf(Color(0xFFE5F8F3), Color(0xFFF4FAF9)),
                        ),
                    ),
            ) {
                FeatureArtwork(isAirport = illustration)
                Surface(
                    modifier = Modifier.align(Alignment.TopEnd).padding(10.dp),
                    shape = RoundedCornerShape(12.dp),
                    color = SoftMint.copy(alpha = 0.94f),
                ) {
                    Text(
                        if (illustration) "✈" else "☑",
                        fontSize = 22.sp,
                        color = Color(0xFF087E79),
                        modifier = Modifier.padding(horizontal = 9.dp, vertical = 4.dp),
                    )
                }
            }
            Column(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 13.dp),
                verticalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                Text(
                    title,
                    fontSize = 14.sp,
                    lineHeight = 23.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = Ink,
                    maxLines = 2,
                )
                Text(
                    detail,
                    fontSize = 11.sp,
                    lineHeight = 19.sp,
                    color = Muted,
                    maxLines = 3,
                    minLines = 2,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    if (badge != null) {
                        Text(
                            badge,
                            color = Ocean,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 10.sp,
                        )
                    } else {
                        Text(
                            stringResource(R.string.premium_open),
                            color = Ocean,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                    Surface(
                        color = Sky,
                        shape = RoundedCornerShape(10.dp),
                    ) {
                        Text(
                            "←",
                            color = Ocean,
                            fontSize = 16.sp,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun BoxScope.FeatureArtwork(isAirport: Boolean) {
    Canvas(modifier = Modifier.matchParentSize()) {
        val w = size.width
        val h = size.height
        if (isAirport) {
            // Terminal silhouette and air traffic control tower.
            drawRoundRect(
                color = Color(0xFF76B5D0),
                topLeft = Offset(w * 0.06f, h * 0.67f),
                size = Size(w * 0.83f, h * 0.33f),
                cornerRadius = CornerRadius(17f, 17f),
            )
            drawRoundRect(
                color = Color(0xFFEBF9FF),
                topLeft = Offset(w * 0.10f, h * 0.72f),
                size = Size(w * 0.76f, h * 0.24f),
                cornerRadius = CornerRadius(11f, 11f),
            )
            for (i in 1..5) {
                val x = w * (0.10f + 0.12f * i)
                drawLine(Color(0xFF7BAFCB), Offset(x, h * 0.74f), Offset(x, h), 2f)
            }
            drawRoundRect(
                Color(0xFF9BB6C5),
                topLeft = Offset(w * 0.25f, h * 0.30f),
                size = Size(w * 0.13f, h * 0.55f),
                cornerRadius = CornerRadius(5f, 5f),
            )
            drawRoundRect(
                Color(0xFF184D70),
                topLeft = Offset(w * 0.20f, h * 0.27f),
                size = Size(w * 0.23f, h * 0.15f),
                cornerRadius = CornerRadius(10f, 10f),
            )
            drawLine(Color(0xFFDBF8FF), Offset(w * 0.23f, h * 0.34f),
                Offset(w * 0.40f, h * 0.34f), 2f)
        } else {
            // Suitcase + passport: travel preparedness, not a misleading booking UI.
            drawRoundRect(
                color = Color(0xFF275C77),
                topLeft = Offset(w * 0.29f, h * 0.20f),
                size = Size(w * 0.42f, h * 0.76f),
                cornerRadius = CornerRadius(22f, 22f),
            )
            drawRoundRect(
                color = Color(0xFF8AAFD0),
                topLeft = Offset(w * 0.44f, h * 0.08f),
                size = Size(w * 0.15f, h * 0.18f),
                cornerRadius = CornerRadius(8f, 8f),
                style = Stroke(width = 6f),
            )
            for (i in 1..3) {
                val x = w * (0.29f + 0.10f * i)
                drawLine(Color(0xFF4C89A8), Offset(x, h * 0.28f),
                    Offset(x, h * 0.87f), 3f)
            }
            drawRoundRect(
                color = Color(0xFFF9FCFF),
                topLeft = Offset(w * 0.10f, h * 0.58f),
                size = Size(w * 0.30f, h * 0.36f),
                cornerRadius = CornerRadius(13f, 13f),
            )
            drawCircle(Color(0xFF43B8A4), w * 0.055f,
                Offset(w * 0.25f, h * 0.75f))
        }
    }
}

@Composable
internal fun PremiumTravelServices(
    onAllServices: () -> Unit,
    onSelect: (HomeDestination) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(
                stringResource(R.string.premium_services_title),
                fontWeight = FontWeight.ExtraBold,
                fontSize = 21.sp,
                color = Ink,
            )
            TextButton(onClick = onAllServices) {
                Text(stringResource(R.string.premium_all_services), fontSize = 12.sp)
                Spacer(Modifier.width(3.dp))
                Text("←", fontSize = 16.sp)
            }
        }
        // The pictured hotel/car/insurance products have not been implemented.
        // Only present actual supported app/Telegram destinations to users.
        BoxWithConstraints {
            if (maxWidth < 350.dp) {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        PremiumServiceTile("قیمت بلیت", "↗", Color(0xFFDDEBFD),
                            Modifier.weight(1f)) { onSelect(HomeDestination.TICKET_PRICES) }
                        PremiumServiceTile("راهنمای ویزا", "▣", Color(0xFFE4F8F3),
                            Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_VISA) }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        PremiumServiceTile("اطلاعات سفر", "✧", Color(0xFFF2E9FC),
                            Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_USEFUL) }
                        PremiumServiceTile("پشتیبانی", "✉", Color(0xFFFFEEDD),
                            Modifier.weight(1f)) { onSelect(HomeDestination.SUPPORT) }
                    }
                }
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                    PremiumServiceTile("قیمت بلیت", "↗", Color(0xFFDDEBFD),
                        Modifier.weight(1f)) { onSelect(HomeDestination.TICKET_PRICES) }
                    PremiumServiceTile("راهنمای ویزا", "▣", Color(0xFFE4F8F3),
                        Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_VISA) }
                    PremiumServiceTile("اطلاعات سفر", "✧", Color(0xFFF2E9FC),
                        Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_USEFUL) }
                    PremiumServiceTile("پشتیبانی", "✉", Color(0xFFFFEEDD),
                        Modifier.weight(1f)) { onSelect(HomeDestination.SUPPORT) }
                }
            }
        }
    }
}

@Composable
private fun PremiumServiceTile(
    title: String,
    symbol: String,
    tint: Color,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Card(
        onClick = onClick,
        modifier = modifier,
        shape = RoundedCornerShape(19.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Outline),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 5.dp, vertical = 13.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Surface(
                color = tint,
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.size(49.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(symbol, fontSize = 23.sp, color = Ocean, fontWeight = FontWeight.Bold)
                }
            }
            Text(
                title,
                fontSize = 11.sp,
                lineHeight = 17.sp,
                textAlign = TextAlign.Center,
                fontWeight = FontWeight.SemiBold,
                color = Ink,
                maxLines = 2,
                minLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun PremiumSectionTitle(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(
            title,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.ExtraBold,
            color = Ink,
        )
        Text(
            subtitle,
            style = MaterialTheme.typography.bodySmall,
            color = Muted,
        )
    }
}
