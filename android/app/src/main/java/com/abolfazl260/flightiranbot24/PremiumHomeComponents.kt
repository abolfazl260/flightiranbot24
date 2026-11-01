package com.abolfazl260.flightiranbot24

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
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
        // Local WebP art overlays the gradient; Persian copy stays accessible UI text.
        Image(
            painter = painterResource(R.drawable.home_hero_plane),
            contentDescription = null,
            contentScale = ContentScale.FillBounds,
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .fillMaxWidth(0.74f)
                .height(142.dp),
        )
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
        // The pictured hotel/car/insurance products have not been implemented.
        // Only present actual supported app/Telegram destinations to users.
        BoxWithConstraints {
            if (maxWidth < 350.dp) {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        PremiumServiceTile("قیمت بلیت", R.drawable.home_tickets,
                            Modifier.weight(1f)) { onSelect(HomeDestination.TICKET_PRICES) }
                        PremiumServiceTile("راهنمای ویزا", R.drawable.home_visa,
                            Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_VISA) }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        PremiumServiceTile("اطلاعات سفر", R.drawable.home_travel,
                            Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_USEFUL) }
                        PremiumServiceTile("پشتیبانی", R.drawable.home_support,
                            Modifier.weight(1f)) { onSelect(HomeDestination.SUPPORT) }
                    }
                }
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                    PremiumServiceTile("قیمت بلیت", R.drawable.home_tickets,
                        Modifier.weight(1f)) { onSelect(HomeDestination.TICKET_PRICES) }
                    PremiumServiceTile("راهنمای ویزا", R.drawable.home_visa,
                        Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_VISA) }
                    PremiumServiceTile("اطلاعات سفر", R.drawable.home_travel,
                        Modifier.weight(1f)) { onSelect(HomeDestination.TELEGRAM_USEFUL) }
                    PremiumServiceTile("پشتیبانی", R.drawable.home_support,
                        Modifier.weight(1f)) { onSelect(HomeDestination.SUPPORT) }
                }
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
            Image(
                painter = painterResource(imageRes),
                contentDescription = null,
                modifier = Modifier
                    .size(66.dp)
                    .clip(RoundedCornerShape(16.dp)),
                contentScale = ContentScale.Crop,
            )
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
