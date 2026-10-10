package com.abolfazl260.flightiranbot24

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.abolfazl260.flightiranbot24.di.AppContainer
import com.abolfazl260.flightiranbot24.domain.HomeDestination
import com.abolfazl260.flightiranbot24.presentation.home.HomeUiState
import com.abolfazl260.flightiranbot24.presentation.home.HomeViewModel
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import com.abolfazl260.flightiranbot24.presentation.components.TravelServiceCard
import com.abolfazl260.flightiranbot24.presentation.components.TravelNavigationItem
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelSectionHeading

/** Persian RTL travel launcher. Offline tools remain local and online features open Telegram. */
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
        if (BuildConfig.APP_ENVIRONMENT != "production" &&
            destination != HomeDestination.OFFLINE_AIRPORTS &&
            destination != HomeDestination.OFFLINE_CHECKLIST &&
            destination != HomeDestination.PRIVACY
        ) {
            Toast.makeText(this, R.string.test_build_online_disabled, Toast.LENGTH_LONG).show()
            return
        }
        when (destination) {
            HomeDestination.OFFLINE_AIRPORTS ->
                startActivity(Intent(this, AirportDirectoryActivity::class.java))
            HomeDestination.OFFLINE_CHECKLIST ->
                startActivity(Intent(this, ChecklistActivity::class.java))
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
            NavigationBar {
                TravelNavigationItem(
                    selected = !showServices,
                    onClick = { showServices = false },
                    symbol = "⌂",
                    label = stringResource(R.string.navigation_home),
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
                    symbol = "✓",
                    label = stringResource(R.string.navigation_checklist),
                )
                TravelNavigationItem(
                    selected = showServices,
                    onClick = { showServices = true },
                    symbol = "☰",
                    label = stringResource(R.string.navigation_services),
                )
            }
        },
    ) { screenPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(screenPadding)
                .windowInsetsPadding(androidx.compose.foundation.layout.WindowInsets.safeDrawing)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondary),
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = stringResource(R.string.welcome_title),
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                    )
                    Text(
                        text = stringResource(R.string.welcome_description),
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.White,
                    )
                }
            }
            val environmentLabel = stringResource(R.string.deployment_status)
            if (environmentLabel.isNotBlank()) {
                Text(
                    text = environmentLabel,
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.labelMedium,
                )
            }

            when (state) {
                HomeUiState.Loading -> TravelLoadingState()
                HomeUiState.Error -> TravelErrorState(
                    message = stringResource(R.string.home_load_error),
                    onRetry = onRetry,
                )
                is HomeUiState.Ready -> {
                    if (!showServices) {
                        ShortcutSection(
                            title = stringResource(R.string.home_offline_heading),
                            description = stringResource(R.string.home_offline_hint),
                            destinations = state.sections.offline,
                            onSelect = onSelect,
                        )
                        ShortcutSection(
                            title = stringResource(R.string.home_quick_services),
                            description = stringResource(R.string.online_service_hint),
                            destinations = state.sections.online.filter {
                                it in listOf(
                                    HomeDestination.TELEGRAM_VISA,
                                    HomeDestination.TELEGRAM_USEFUL,
                                    HomeDestination.SUPPORT,
                                ) && (BuildConfig.APP_ENVIRONMENT == "production")
                            },
                            onSelect = onSelect,
                        )
                    } else {
                        ShortcutSection(
                            title = stringResource(R.string.home_online_heading),
                            description = stringResource(R.string.online_service_hint),
                            destinations = if (BuildConfig.APP_ENVIRONMENT == "production") {
                                state.sections.online
                            } else {
                                state.sections.online.filter { it == HomeDestination.PRIVACY }
                            },
                            onSelect = onSelect,
                        )
                    }
                }
            }

            Text(
                text = stringResource(R.string.notice),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Start,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun ShortcutSection(
    title: String,
    description: String,
    destinations: List<HomeDestination>,
    onSelect: (HomeDestination) -> Unit,
) {
    if (destinations.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        TravelSectionHeading(title = title, description = description)
        destinations.forEach { destination ->
            TravelServiceCard(
                title = stringResource(destination.labelResource()),
                subtitle = stringResource(
                    if (destination.isLocal()) R.string.home_local_badge
                    else R.string.home_external_badge
                ),
                symbol = destination.symbol(),
                onClick = { onSelect(destination) },
            )
        }
    }
}

private fun HomeDestination.isLocal(): Boolean =
    this == HomeDestination.OFFLINE_AIRPORTS || this == HomeDestination.OFFLINE_CHECKLIST

private fun HomeDestination.symbol(): String = when (this) {
    HomeDestination.OFFLINE_AIRPORTS -> "✈"
    HomeDestination.OFFLINE_CHECKLIST -> "☑"
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
    HomeDestination.TELEGRAM_BOT -> R.string.open_bot
    HomeDestination.TELEGRAM_VISA -> R.string.open_visa
    HomeDestination.TELEGRAM_AIRPORTS -> R.string.open_airports
    HomeDestination.TELEGRAM_USEFUL -> R.string.open_useful
    HomeDestination.SUPPORT -> R.string.open_support
    HomeDestination.PRIVACY -> R.string.open_privacy
}
