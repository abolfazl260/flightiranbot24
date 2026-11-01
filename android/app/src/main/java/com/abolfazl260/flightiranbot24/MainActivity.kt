package com.abolfazl260.flightiranbot24

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
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
            HomeDestination.OFFLINE_AIRPORTS, HomeDestination.TELEGRAM_AIRPORTS ->
                Toast.makeText(this, R.string.airports_coming_soon_message, Toast.LENGTH_LONG).show()
            HomeDestination.OFFLINE_CHECKLIST ->
                startActivity(Intent(this, ChecklistActivity::class.java))
            HomeDestination.TICKET_PRICES ->
                startActivity(Intent(this, TicketPricesActivity::class.java))
            HomeDestination.IRAN_FLIGHTS ->
                startActivity(Intent(this, IranFlightsActivity::class.java))
            HomeDestination.TELEGRAM_BOT -> openUrl(BotLinks.BOT)
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
    // Separate scroll offsets: opening Services from a home card must start at
    // the top rather than inheriting the user's previous home scroll position.
    val homeScroll = rememberScrollState()
    val servicesScroll = rememberScrollState()
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            Surface(
                shape = RoundedCornerShape(topStart = 26.dp, topEnd = 26.dp),
                color = Color.White,
                shadowElevation = 8.dp,
            ) {
                NavigationBar(
                    containerColor = Color.White,
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
            }
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .windowInsetsPadding(androidx.compose.foundation.layout.WindowInsets.safeDrawing)
                .verticalScroll(if (showServices) servicesScroll else homeScroll)
                .padding(horizontal = 16.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(26.dp),
        ) {
            if (!showServices) {
                PremiumHomeHero(onPrices = { onSelect(HomeDestination.TICKET_PRICES) })
                when (state) {
                    HomeUiState.Loading -> TravelLoadingState()
                    HomeUiState.Error -> TravelErrorState(
                        message = stringResource(R.string.home_load_error),
                        onRetry = onRetry,
                    )
                    is HomeUiState.Ready -> {
                        PremiumPreparationSection(
                            onChecklist = { onSelect(HomeDestination.OFFLINE_CHECKLIST) },
                            // Airports are still unavailable; this card opens
                            // the existing Services tab, never AirportDirectoryActivity.
                            onAirportServices = { showServices = true },
                        )
                        PremiumTravelServices(
                            onAllServices = { showServices = true },
                            onSelect = onSelect,
                        )
                    }
                }
            } else {
                Text(
                    stringResource(R.string.home_online_heading),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.ExtraBold,
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
    HomeDestination.IRAN_FLIGHTS -> "◷"
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
    HomeDestination.IRAN_FLIGHTS -> R.string.iran_fids_title
    HomeDestination.TELEGRAM_BOT -> R.string.open_bot
    HomeDestination.TELEGRAM_VISA -> R.string.open_visa
    HomeDestination.TELEGRAM_AIRPORTS -> R.string.open_airports
    HomeDestination.TELEGRAM_USEFUL -> R.string.open_useful
    HomeDestination.SUPPORT -> R.string.open_support
    HomeDestination.PRIVACY -> R.string.open_privacy
}
