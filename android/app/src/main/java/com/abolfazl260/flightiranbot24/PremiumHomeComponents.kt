package com.abolfazl260.flightiranbot24

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.abolfazl260.flightiranbot24.domain.HomeDestination

// Persian-first Android dashboard using bundled, offline WebP travel artwork.
// Text and actions remain native Compose for accessibility and responsive layout.
private val Midnight = Color(0xFF062D4D)
private val Ocean = Color(0xFF0C557D)
private val Mint = Color(0xFFBFEFE3)
private val Ink = Color(0xFF0D2C44)
private val Muted = Color(0xFF5D6D7D)
private val Outline = Color(0xFFE0EAF0)
private val Sky = Color(0xFFDFEFFB)

@Composable
internal fun PremiumHomeHero(onPrices: () -> Unit) {
    val bannerDescription = stringResource(R.string.hero_banner_accessibility)
    // Artwork includes the copy and call-to-action. Render the entire image at
    // its native aspect ratio: no crop, stretching, or duplicated Compose text.
    // The whole card remains an accessible, native click target.
    Card(
        onClick = onPrices,
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1672f / 941f)
            .semantics { contentDescription = bannerDescription },
        shape = RoundedCornerShape(29.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 9.dp),
    ) {
        Image(
            painter = painterResource(R.drawable.home_hero_plane),
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier.fillMaxSize(),
        )
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
                imageRes = R.drawable.home_checklist,
                badge = null,
                onClick = onChecklist,
            )
            PremiumFeatureCard(
                modifier = Modifier.weight(1f),
                title = stringResource(R.string.offline_airports),
                detail = stringResource(R.string.premium_airport_description),
                imageRes = R.drawable.home_airport,
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
    imageRes: Int,
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
            Image(
                painter = painterResource(imageRes),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxWidth().height(130.dp),
            )
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
        // The four bundled WebP images include their own Persian titles.
        // Two columns keep the artwork legible, including on narrow phones.
        Column(
            modifier = Modifier.fillMaxWidth().widthIn(max = 560.dp)
                .align(Alignment.CenterHorizontally),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                PremiumServiceTile("قیمت بلیت", R.drawable.home_tickets,
                    Modifier.weight(1f)) { onSelect(HomeDestination.TICKET_PRICES) }
                PremiumServiceTile("راهنمای ویزا", R.drawable.home_visa,
                    Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_VISA) }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                PremiumServiceTile("خدمات سفر", R.drawable.home_travel,
                    Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_USEFUL) }
                PremiumServiceTile("پشتیبانی", R.drawable.home_support,
                    Modifier.weight(1f)) { onSelect(HomeDestination.SUPPORT) }
            }
        }
    }
}

@Composable
private fun PremiumServiceTile(
    title: String,
    imageRes: Int,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Card(
        onClick = onClick,
        // Keep a screen-reader label even though the visible title is baked
        // into the image; the entire artwork stays a tappable target.
        modifier = modifier.semantics { contentDescription = title },
        shape = RoundedCornerShape(19.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Image(
            painter = painterResource(imageRes),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxWidth().aspectRatio(1f),
        )
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
