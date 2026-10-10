package com.abolfazl260.flightiranbot24

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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

/**
 * Compose presentation backed by lifecycle-aware ViewModel state (AND-002).
 * Airports and checklist remain the existing native Java Activities.
 */
class MainActivity : ComponentActivity() {
    private val container by lazy { AppContainer() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val model: HomeViewModel = viewModel(factory = container.homeViewModelFactory)
            val screenState by model.state.collectAsStateWithLifecycle()
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    TravelHomeScreen(
                        state = screenState,
                        onSelect = ::navigateTo,
                        onRetry = model::refresh,
                    )
                }
            }
        }
    }

    private fun navigateTo(destination: HomeDestination) {
        when (destination) {
            HomeDestination.OFFLINE_AIRPORTS ->
                startActivity(Intent(this, AirportDirectoryActivity::class.java))
            HomeDestination.OFFLINE_CHECKLIST ->
                startActivity(Intent(this, ChecklistActivity::class.java))
            HomeDestination.TELEGRAM_BOT,
            HomeDestination.TELEGRAM_AIRPORTS,
            HomeDestination.TELEGRAM_USEFUL -> openUrl(BotLinks.BOT)
            HomeDestination.TELEGRAM_VISA -> openBotCommand("/visa")
            HomeDestination.SUPPORT -> openUrl(BotLinks.SUPPORT)
            HomeDestination.PRIVACY -> openUrl(BotLinks.PRIVACY)
        }
    }

    private fun openBotCommand(command: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
        clipboard?.setPrimaryClip(ClipData.newPlainText("Telegram command", command))
        if (clipboard != null) {
            Toast.makeText(this, R.string.command_copied, Toast.LENGTH_SHORT).show()
        }
        openUrl(BotLinks.BOT)
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
    Column(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(WindowInsets.safeDrawing)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = stringResource(R.string.welcome_title),
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
        )
        Text(
            text = stringResource(R.string.welcome_description),
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
        )
        when (state) {
            HomeUiState.Loading -> CircularProgressIndicator()
            HomeUiState.Error -> {
                Text(
                    text = stringResource(R.string.home_load_error),
                    style = MaterialTheme.typography.bodyLarge,
                )
                Button(onClick = onRetry) {
                    Text(stringResource(R.string.home_retry))
                }
            }
            is HomeUiState.Ready -> {
                ShortcutSection(
                    title = stringResource(R.string.home_offline_heading),
                    destinations = state.sections.offline,
                    onSelect = onSelect,
                )
                ShortcutSection(
                    title = stringResource(R.string.home_online_heading),
                    destinations = state.sections.online,
                    onSelect = onSelect,
                )
            }
        }
        Text(
            text = stringResource(R.string.command_hint),
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
        )
        Text(
            text = stringResource(R.string.notice),
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
private fun ShortcutSection(
    title: String,
    destinations: List<HomeDestination>,
    onSelect: (HomeDestination) -> Unit,
) {
    Text(
        text = title,
        style = MaterialTheme.typography.titleMedium,
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
    )
    destinations.forEach { destination ->
        Button(
            onClick = { onSelect(destination) },
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        ) {
            Text(
                text = stringResource(destination.labelResource()),
                textAlign = TextAlign.Center,
            )
        }
    }
}

/** Presentation-only labels: domain and ViewModel have no Android R dependency. */
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
