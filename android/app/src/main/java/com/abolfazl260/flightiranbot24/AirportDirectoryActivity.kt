package com.abolfazl260.flightiranbot24

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.abolfazl260.flightiranbot24.presentation.components.TravelToolbar
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import java.util.Locale

/**
 * Match the Telegram Mini App: the airport search is not released yet.
 * No airport data or search UI is loaded while this feature is unavailable.
 */
class AirportDirectoryActivity : ComponentActivity() {
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TravelTheme {
                AirportComingSoonScreen(onBack = { finish() })
            }
        }
    }
}

@Composable
internal fun AirportComingSoonScreen(onBack: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(androidx.compose.foundation.layout.WindowInsets.safeDrawing)
            .padding(horizontal = 20.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp),
    ) {
        TravelToolbar(
            title = stringResource(R.string.navigation_airports),
            onBack = onBack,
        )
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        ) {
            Column(
                modifier = Modifier.fillMaxWidth().padding(28.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = "✈",
                    style = MaterialTheme.typography.headlineLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(
                    text = stringResource(R.string.airports_coming_soon_title),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center,
                )
                Text(
                    text = stringResource(R.string.airports_coming_soon_message),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
                TextButton(onClick = onBack) {
                    Text(stringResource(R.string.airports_back_home))
                }
            }
        }
    }
}

// Future airport-search domain helpers remain tested, but cannot be reached
// from any current app entry point until this feature is explicitly launched.
internal data class AirportRow(
    val code: String,
    val name: String,
    val country: String,
    val timezone: String,
    val aliases: List<String> = emptyList(),
)

private fun String.normalizedSearch(): String =
    trim().lowercase(Locale.ROOT).replace('ي', 'ی').replace('ك', 'ک')

internal fun filterAirports(rows: List<AirportRow>, search: String): List<AirportRow> {
    val query = search.normalizedSearch()
    if (query.isBlank()) return rows.sortedBy { it.name }
    return rows.filter { airport ->
        listOf(airport.code, airport.name, airport.country, airport.timezone, *airport.aliases.toTypedArray())
            .any { it.normalizedSearch().contains(query) }
    }.sortedBy { it.name }
}
