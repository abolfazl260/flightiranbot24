package com.abolfazl260.flightiranbot24

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.abolfazl260.flightiranbot24.di.AppContainer
import com.abolfazl260.flightiranbot24.domain.HomeDestination
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelNavigationItem
import com.abolfazl260.flightiranbot24.presentation.home.HomeUiState
import com.abolfazl260.flightiranbot24.presentation.home.HomeViewModel
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme

/** Persian-only RTL launcher with calm, minimal Material 3 surfaces and real navigation. */
class MainActivity : ComponentActivity() {
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    private val container by lazy { AppContainer(applicationContext) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val model: HomeViewModel = viewModel(factory = container.homeViewModelFactory)
            val screenState by model.state.collectAsStateWithLifecycle()
            TravelTheme {
                TravelHomeScreen(
                    state = screenState,
                    onSelect = ::navigateTo,
                    onRetry = model::refresh,
                )
            }
        }
    }

    private fun navigateTo(destination: HomeDestination) {
        when (destination) {
            HomeDestination.OFFLINE_AIRPORTS ->
                startActivity(Intent(this, AirportDirectoryActivity::class.java))
            HomeDestination.OFFLINE_CHECKLIST ->
                startActivity(Intent(this, ChecklistActivity::class.java))
            HomeDestination.TICKET_PRICES ->
                startActivity(Intent(this, TicketPricesActivity::class.java))
            HomeDestination.TELEGRAM_BOT -> openUrl(BotLinks.BOT)
            HomeDestination.TELEGRAM_AIRPORTS -> openUrl(BotLinks.AIRPORTS)
            HomeDestination.TELEGRAM_USEFUL -> openUrl(BotLinks.USEFUL)
            HomeDestination.TELEGRAM_VISA -> openUrl(BotLinks.VISA)
            HomeDestination.SUPPORT -> openUrl(BotLinks.SUPPORT)
            HomeDestination.PRIVACY -> openUrl(BotLinks.PRIVACY)
        }
    }

    private fun openUrl(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, R.string.link_unavailable, Toast.LENGTH_LONG).show()
        }
    }
}

@Composable
internal fun TravelHomeScreen(
    state: HomeUiState,
    onSelect: (HomeDestination) -> Unit,
    onRetry: () -> Unit,
) {
    var showServices by rememberSaveable { mutableStateOf(false) }
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
                tonalElevation = 0.dp,
            ) {
                TravelNavigationItem(
                    selected = !showServices,
                    onClick = { showServices = false },
                    symbol = "⌂",
                    label = stringResource(R.string.navigation_home),
                )
                TravelNavigationItem(
                    selected = false,
                    onClick = { onSelect(HomeDestination.TICKET_PRICES) },
                    symbol = "↗",
                    label = stringResource(R.string.navigation_prices),
                )
                TravelNavigationItem(
                    selected = false,
                    onClick = { onSelect(HomeDestination.OFFLINE_AIRPORTS) },
                    symbol = "✈",
                    label = stringResource(R.string.navigation_airports),
                )
                TravelNavigationItem(
                    selected = false,
                    onClick = { onSelect(HomeDestination.OFFLINE_CHECKLIST) },
                    symbol = "☑",
                    label = stringResource(R.string.navigation_checklist),
                )
                TravelNavigationItem(
                    selected = showServices,
                    onClick = { showServices = true },
                    symbol = "☷",
                    label = stringResource(R.string.navigation_services),
                )
            }
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .windowInsetsPadding(androidx.compose.foundation.layout.WindowInsets.safeDrawing)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(24.dp),
        ) {
            HomeBrandBar()
            if (!showServices) {
                HomeHero(onTickets = { onSelect(HomeDestination.TICKET_PRICES) })
                when (state) {
                    HomeUiState.Loading -> TravelLoadingState()
                    HomeUiState.Error -> TravelErrorState(
                        message = stringResource(R.string.home_load_error),
                        onRetry = onRetry,
                    )
                    is HomeUiState.Ready -> {
                        HomeFeatureGrid(onSelect)
                        HomeTicketHighlight(onClick = { onSelect(HomeDestination.TICKET_PRICES) })
                        HomeQuickServices(onSelect)
                    }
                }
            } else {
                Text(
                    stringResource(R.string.home_online_heading),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    stringResource(R.string.home_services_hint),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                when (state) {
                    HomeUiState.Loading -> TravelLoadingState()
                    HomeUiState.Error -> TravelErrorState(
                        message = stringResource(R.string.home_load_error),
                        onRetry = onRetry,
                    )
                    is HomeUiState.Ready ->
                        state.sections.online.forEach { destination ->
                            HomeServiceRow(destination, onClick = { onSelect(destination) })
                        }
                }
            }
            Text(
                stringResource(R.string.notice),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Start,
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
            )
        }
    }
}

@Composable
private fun HomeBrandBar() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Image(
            painter = painterResource(id = R.drawable.advertio_brand),
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier.size(52.dp),
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                "ADVERTIO",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = 1.6.sp,
            )
            Text(
                "دستیار هوشمند سفر",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.labelSmall,
            )
        }
        Surface(
            shape = RoundedCornerShape(50),
            color = MaterialTheme.colorScheme.primaryContainer,
        ) {
            Text(
                "همراه سفر شما",
                color = MaterialTheme.colorScheme.primary,
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 9.dp),
            )
        }
    }
}

@Composable
private fun HomeHero(onTickets: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(26.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondary),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 23.dp, vertical = 24.dp),
            verticalArrangement = Arrangement.spacedBy(15.dp),
        ) {
            Text(
                stringResource(R.string.hero_eyebrow),
                color = MaterialTheme.colorScheme.primaryContainer,
                style = MaterialTheme.typography.labelSmall,
                letterSpacing = 0.4.sp,
            )
            Text(
                stringResource(R.string.welcome_title),
                color = Color.White,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                stringResource(R.string.welcome_description),
                color = Color.White.copy(alpha = 0.8f),
                style = MaterialTheme.typography.bodyMedium,
            )
            Spacer(Modifier.height(1.dp))
            Button(
                onClick = onTickets,
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.White,
                    contentColor = MaterialTheme.colorScheme.secondary,
                ),
                contentPadding = PaddingValues(horizontal = 17.dp, vertical = 12.dp),
            ) {
                Text(stringResource(R.string.hero_action), fontWeight = FontWeight.Bold)
                Text("  ←", fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun HomeFeatureGrid(onSelect: (HomeDestination) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        HomeSectionHeading(
            stringResource(R.string.home_offline_heading),
            stringResource(R.string.home_tools_hint),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            HomeFeatureCard(
                title = stringResource(R.string.checklist_title),
                subtitle = "۱۲ گام برای آمادگی",
                symbol = "☑",
                modifier = Modifier.weight(1f),
                onClick = { onSelect(HomeDestination.OFFLINE_CHECKLIST) },
            )
            HomeFeatureCard(
                title = stringResource(R.string.offline_airports),
                subtitle = "جست‌وجوی فرودگاه‌ها",
                symbol = "✈",
                modifier = Modifier.weight(1f),
                onClick = { onSelect(HomeDestination.OFFLINE_AIRPORTS) },
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            HomeFeatureCard(
                title = stringResource(R.string.open_visa),
                subtitle = "مدارک و شرایط ورود",
                symbol = "▣",
                modifier = Modifier.weight(1f),
                onClick = { onSelect(HomeDestination.TELEGRAM_VISA) },
            )
            HomeFeatureCard(
                title = stringResource(R.string.open_useful),
                subtitle = "نکته‌های کاربردی سفر",
                symbol = "✧",
                modifier = Modifier.weight(1f),
                onClick = { onSelect(HomeDestination.TELEGRAM_USEFUL) },
            )
        }
    }
}

@Composable
private fun HomeFeatureCard(
    title: String,
    subtitle: String,
    symbol: String,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Card(
        onClick = onClick,
        modifier = modifier,
        shape = RoundedCornerShape(19.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.6f)),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(17.dp),
            verticalArrangement = Arrangement.spacedBy(7.dp),
        ) {
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.primaryContainer,
            ) {
                Text(
                    symbol,
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 5.dp),
                )
            }
            Spacer(Modifier.height(3.dp))
            Text(title, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
            Text(
                subtitle,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun HomeTicketHighlight(onClick: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(11.dp)) {
        HomeSectionHeading(
            stringResource(R.string.home_fares_tile_title),
            stringResource(R.string.home_fares_tile_hint),
        )
        Card(
            onClick = onClick,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(19.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(19.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Text(
                    "↗",
                    style = MaterialTheme.typography.headlineMedium,
                    color = MaterialTheme.colorScheme.primary,
                )
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        stringResource(R.string.ticket_prices_title),
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Text(
                        stringResource(R.string.home_fares_tile_hint),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Text("←", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun HomeQuickServices(onSelect: (HomeDestination) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(11.dp)) {
        HomeSectionHeading(
            stringResource(R.string.home_quick_services),
            stringResource(R.string.home_services_hint),
        )
        HomeServiceRow(HomeDestination.SUPPORT) { onSelect(HomeDestination.SUPPORT) }
        HomeServiceRow(HomeDestination.TELEGRAM_BOT) { onSelect(HomeDestination.TELEGRAM_BOT) }
    }
}

@Composable
private fun HomeServiceRow(destination: HomeDestination, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.6f)),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 15.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                destination.symbol(),
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                stringResource(destination.labelResource()),
                modifier = Modifier.weight(1f),
                fontWeight = FontWeight.Medium,
                style = MaterialTheme.typography.bodyMedium,
            )
            Text("‹", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun HomeSectionHeading(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text(
            subtitle,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

private fun HomeDestination.symbol(): String = when (this) {
    HomeDestination.OFFLINE_AIRPORTS -> "✈"
    HomeDestination.OFFLINE_CHECKLIST -> "☑"
    HomeDestination.TICKET_PRICES -> "↗"
    HomeDestination.TELEGRAM_BOT -> "✦"
    HomeDestination.TELEGRAM_VISA -> "▣"
    HomeDestination.TELEGRAM_AIRPORTS -> "⌖"
    HomeDestination.TELEGRAM_USEFUL -> "✧"
    HomeDestination.SUPPORT -> "✉"
    HomeDestination.PRIVACY -> "◈"
}

private fun HomeDestination.labelResource(): Int = when (this) {
    HomeDestination.OFFLINE_AIRPORTS -> R.string.offline_airports
    HomeDestination.OFFLINE_CHECKLIST -> R.string.checklist_title
    HomeDestination.TICKET_PRICES -> R.string.ticket_prices_title
    HomeDestination.TELEGRAM_BOT -> R.string.open_bot
    HomeDestination.TELEGRAM_VISA -> R.string.open_visa
    HomeDestination.TELEGRAM_AIRPORTS -> R.string.open_airports
    HomeDestination.TELEGRAM_USEFUL -> R.string.open_useful
    HomeDestination.SUPPORT -> R.string.open_support
    HomeDestination.PRIVACY -> R.string.open_privacy
}
