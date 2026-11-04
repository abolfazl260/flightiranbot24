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
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Alignment
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.imageResource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.sp
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
            HomeDestination.AIRLINES ->
                startActivity(Intent(this, AirlineDirectoryActivity::class.java))
            HomeDestination.OFFLINE_AIRPORTS, HomeDestination.TELEGRAM_AIRPORTS ->
                startActivity(Intent(this, AirportDirectoryActivity::class.java))
            HomeDestination.OFFLINE_CHECKLIST ->
                startActivity(Intent(this, ChecklistActivity::class.java))
            HomeDestination.TICKET_PRICES ->
                startActivity(Intent(this, TicketPricesActivity::class.java))
            HomeDestination.IRAN_FLIGHTS ->
                startActivity(Intent(this, IranFlightsActivity::class.java))
            HomeDestination.TELEGRAM_BOT -> openUrl(BotLinks.BOT)
            HomeDestination.TELEGRAM_USEFUL ->
                startActivity(Intent(this, TravelWebsitesActivity::class.java))
            HomeDestination.TELEGRAM_VISA ->
                startActivity(Intent(this, VisaGuideActivity::class.java))
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
            verticalArrangement = Arrangement.spacedBy(if (showServices) 12.dp else 26.dp),
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
                            onAirportServices = { onSelect(HomeDestination.OFFLINE_AIRPORTS) },
                        )
                        PremiumTravelServices(
                            onAllServices = { changeTab(true) },
                            onSelect = onSelect,
                        )
                    }
                }
            } else {
                Text(
                    stringResource(R.string.premium_services_title),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.ExtraBold,
                )
                Text(
                    stringResource(R.string.services_page_subtitle),
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

/**
 * The transparent WebP atlas contains seven crisp 160px 3D icons
 * downsampled from high-resolution originals. Render each at 52dp with
 * high-quality filtering; never upscale the previous 80px sprite.
 * No colored backing, frame, or text is baked into the artwork.
 */
@Composable
private fun HomeServiceRow(destination: HomeDestination, onClick: () -> Unit) {
    val icons = ImageBitmap.imageResource(R.drawable.service_icons_atlas)
    val slot = destination.serviceIconSlot()
    val slotWidth = icons.width / 7
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().heightIn(min = 76.dp),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.45f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Canvas(modifier = Modifier.size(52.dp)) {
                drawImage(
                    image = icons,
                    srcOffset = IntOffset(slot * slotWidth, 0),
                    srcSize = IntSize(slotWidth, icons.height),
                    dstSize = IntSize(size.width.toInt(), size.height.toInt()),
                    filterQuality = FilterQuality.High,
                )
            }
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    stringResource(destination.labelResource()),
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    stringResource(destination.serviceDescriptionResource()),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Text(
                "‹",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

private fun HomeDestination.serviceIconSlot(): Int = when (this) {
    HomeDestination.AIRLINES -> 1
    HomeDestination.TICKET_PRICES -> 0
    HomeDestination.IRAN_FLIGHTS, HomeDestination.TELEGRAM_AIRPORTS,
    HomeDestination.OFFLINE_AIRPORTS -> 1
    HomeDestination.TELEGRAM_BOT, HomeDestination.OFFLINE_CHECKLIST -> 2
    HomeDestination.TELEGRAM_VISA -> 3
    HomeDestination.TELEGRAM_USEFUL -> 4
    HomeDestination.SUPPORT -> 5
    HomeDestination.PRIVACY -> 6
}

private fun HomeDestination.serviceDescriptionResource(): Int = when (this) {
    HomeDestination.AIRLINES -> R.string.service_airlines_description
    HomeDestination.TICKET_PRICES -> R.string.service_fares_description
    HomeDestination.IRAN_FLIGHTS -> R.string.service_iran_flights_description
    HomeDestination.TELEGRAM_AIRPORTS, HomeDestination.OFFLINE_AIRPORTS ->
        R.string.service_airports_description
    HomeDestination.TELEGRAM_BOT, HomeDestination.OFFLINE_CHECKLIST ->
        R.string.service_assistant_description
    HomeDestination.TELEGRAM_VISA -> R.string.service_visa_description
    HomeDestination.TELEGRAM_USEFUL -> R.string.service_travel_info_description
    HomeDestination.SUPPORT -> R.string.service_support_description
    HomeDestination.PRIVACY -> R.string.service_privacy_description
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

private fun HomeDestination.labelResource(): Int = when (this) {
    HomeDestination.AIRLINES -> R.string.airlines_title
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
