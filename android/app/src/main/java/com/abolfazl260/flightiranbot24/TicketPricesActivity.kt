package com.abolfazl260.flightiranbot24

import android.content.ActivityNotFoundException
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
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.abolfazl260.flightiranbot24.data.tickets.TicketFare
import com.abolfazl260.flightiranbot24.di.AppContainer
import com.abolfazl260.flightiranbot24.presentation.components.TravelEmptyState
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelToolbar
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import com.abolfazl260.flightiranbot24.presentation.tickets.TicketPricesUiState
import com.abolfazl260.flightiranbot24.presentation.tickets.TicketPricesViewModel
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.abs

/** Persian-only RTL fare list; viewing prices never opens Telegram. */
class TicketPricesActivity : ComponentActivity() {
    private val container by lazy { AppContainer(applicationContext) }

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val model: TicketPricesViewModel = viewModel(factory = container.ticketPricesViewModelFactory)
            val state by model.state.collectAsStateWithLifecycle()
            TravelTheme {
                TicketPricesScreen(
                    state = state,
                    onBack = ::finish,
                    onRefresh = model::refresh,
                    onSupport = { openUrl(BotLinks.SUPPORT) },
                    allowSupport = BuildConfig.APP_ENVIRONMENT == "production",
                )
            }
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
internal fun TicketPricesScreen(
    state: TicketPricesUiState,
    onBack: () -> Unit,
    onRefresh: () -> Unit,
    onSupport: () -> Unit,
    allowSupport: Boolean,
) {
    var selectedOrigin by rememberSaveable { mutableStateOf("") }
    var search by rememberSaveable { mutableStateOf("") }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            TravelToolbar(title = stringResource(R.string.ticket_prices_title), onBack = onBack)
            Text(
                stringResource(R.string.ticket_prices_explanation),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        when (state) {
            TicketPricesUiState.Loading -> item { TravelLoadingState() }
            TicketPricesUiState.Unconfigured -> item {
                TravelErrorState(stringResource(R.string.ticket_prices_unconfigured))
            }
            TicketPricesUiState.Error -> item {
                TravelErrorState(stringResource(R.string.ticket_prices_error), onRefresh)
            }
            is TicketPricesUiState.Ready -> {
                val snapshot = state.snapshot
                val active = snapshot.origins.firstOrNull { it.city == selectedOrigin }
                    ?: snapshot.origins.first()
                item {
                    if (snapshot.stale) {
                        Text(
                            stringResource(R.string.ticket_prices_stale),
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                    Text(
                        stringResource(R.string.ticket_prices_observed, snapshot.observedAt.take(16).replace("T", " ")),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodySmall,
                    )
                    TextButton(onClick = onRefresh) {
                        Text(stringResource(R.string.ticket_prices_refresh))
                    }
                }
                item {
                    Text(stringResource(R.string.ticket_prices_origin), fontWeight = FontWeight.Bold)
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(snapshot.origins, key = { it.city }) { route ->
                            FilterChip(
                                selected = route.city == active.city,
                                onClick = { selectedOrigin = route.city; search = "" },
                                label = { Text(route.city) },
                            )
                        }
                    }
                }
                item {
                    OutlinedTextField(
                        value = search,
                        onValueChange = { search = it },
                        label = { Text(stringResource(R.string.ticket_prices_search)) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                    )
                }
                val fares = active.fares.filter {
                    it.destination.contains(search.trim(), ignoreCase = true)
                }.sortedBy { it.currentToman }
                if (fares.isEmpty()) {
                    item { TravelEmptyState(stringResource(R.string.ticket_prices_empty)) }
                } else {
                    items(fares) { fare -> FareCard(fare) }
                }
                if (allowSupport) {
                    item {
                        Button(onClick = onSupport, modifier = Modifier.fillMaxWidth()) {
                            Text(stringResource(R.string.ticket_prices_support))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun FareCard(fare: TicketFare) {
    val number = NumberFormat.getNumberInstance(Locale("fa", "IR"))
    val percent = fare.differencePercent
    val changeColor = when {
        percent == null || abs(percent) < 0.05 -> MaterialTheme.colorScheme.onSurfaceVariant
        percent < 0 -> Color(0xFF166534)
        else -> MaterialTheme.colorScheme.error
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(fare.destination, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(stringResource(R.string.ticket_prices_current))
                Text(
                    stringResource(R.string.ticket_prices_toman, number.format(fare.currentToman)),
                    fontWeight = FontWeight.Bold,
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(stringResource(R.string.ticket_prices_average))
                Text(
                    fare.averageToman?.let {
                        stringResource(R.string.ticket_prices_toman, number.format(it))
                    } ?: stringResource(R.string.ticket_prices_no_average),
                )
            }
            if (percent != null) {
                val sign = when {
                    percent < -0.05 -> "↓"
                    percent > 0.05 -> "↑"
                    else -> "–"
                }
                Text(
                    sign + " " + number.format(abs(percent)) + "٪ نسبت به میانگین",
                    color = changeColor,
                    fontWeight = FontWeight.Medium,
                )
            }
        }
    }
}
