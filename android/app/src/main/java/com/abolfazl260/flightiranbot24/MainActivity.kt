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
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Alignment
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
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
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
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
import com.abolfazl260.flightiranbot24.presentation.components.TravelBottomNavigation
import com.abolfazl260.flightiranbot24.presentation.components.TravelTab
import com.abolfazl260.flightiranbot24.presentation.home.HomeUiState
import com.abolfazl260.flightiranbot24.presentation.home.HomeViewModel
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme

/** Persian-only RTL launcher with calm, minimal Material 3 surfaces and real navigation. */
class MainActivity : ComponentActivity() {
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    private val container by lazy { AppContainer(applicationContext) }
    private var servicesSelected by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        servicesSelected = savedInstanceState?.getBoolean(STATE_SERVICES)
            ?: (intent.getStringExtra(EXTRA_TAB) == TravelTab.SERVICES.name)
        setContent {
            val model: HomeViewModel = viewModel(factory = container.homeViewModelFactory)
            val screenState by model.state.collectAsStateWithLifecycle()
            TravelTheme {
                TravelHomeScreen(
                    state = screenState,
                    onSelect = ::navigateTo,
                    onRetry = model::refresh,
                    selectedServices = servicesSelected,
                    onServiceTabChange = { servicesSelected = it },
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        when (intent.getStringExtra(EXTRA_TAB)) {
            TravelTab.HOME.name -> servicesSelected = false
            TravelTab.SERVICES.name -> servicesSelected = true
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putBoolean(STATE_SERVICES, servicesSelected)
        super.onSaveInstanceState(outState)
    }

    companion object {
        const val EXTRA_TAB = "com.abolfazl260.flightiranbot24.extra.MAIN_TAB"
        private const val STATE_SERVICES = "main_services_selected"
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
            HomeDestination.TELEGRAM_USEFUL ->
                startActivity(Intent(this, TravelWebsitesActivity::class.java))
            HomeDestination.TELEGRAM_VISA -> openUrl(BotLinks.VISA)
            HomeDestination.SUPPORT -> openUrl(BotLinks.SUPPORT)
            HomeDestination.PRIVACY ->
                startActivity(Intent(this, PrivacyPolicyActivity::class.java))
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
    selectedServices: Boolean? = null,
    onServiceTabChange: (Boolean) -> Unit = {},
) {
    var localShowServices by rememberSaveable { mutableStateOf(false) }
    val showServices = selectedServices ?: localShowServices
    val changeTab: (Boolean) -> Unit = { show ->
        localShowServices = show
        onServiceTabChange(show)
    }
    // Separate scroll offsets: opening Services from a home card must start at
    // the top rather than inheriting the user's previous home scroll position.
    val homeScroll = rememberScrollState()
    val servicesScroll = rememberScrollState()
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            TravelBottomNavigation(
                selectedTab = if (showServices) TravelTab.SERVICES else TravelTab.HOME,
                onHome = { changeTab(false) },
                onPrices = { onSelect(HomeDestination.TICKET_PRICES) },
                onChecklist = { onSelect(HomeDestination.OFFLINE_CHECKLIST) },
                onServices = { changeTab(true) },
            )
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
                HomeBrandBar()
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
                            onAirportServices = { changeTab(true) },
                        )
                        PremiumTravelServices(
                            onAllServices = { changeTab(true) },
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
private fun HomeBrandBar() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Image(
            painter = painterResource(R.drawable.advertio_brand),
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier.size(42.dp),
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                "ADVERTIO",
                color = Color(0xFF0D2C44),
                fontWeight = FontWeight.ExtraBold,
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                "دستیار هوشمند سفر",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.labelSmall,
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
