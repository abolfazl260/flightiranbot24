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
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.abs

/** Displays actual database-backed ticket prices; never fabricates route fares. */
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
                    allowSupport = true,
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
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                TravelToolbar(
                    title = stringResource(R.string.ticket_prices_title),
                    onBack = onBack,
                )
                Text(
                    stringResource(R.string.ticket_prices_explanation),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        when (state) {
            TicketPricesUiState.Loading -> item { TravelLoadingState("در حال دریافت قیمت‌های ثبت‌شده…") }
            TicketPricesUiState.Unconfigured -> item {
                TravelErrorState(stringResource(R.string.ticket_prices_unconfigured), onRefresh)
            }
            TicketPricesUiState.Error -> item {
                TravelErrorState(stringResource(R.string.ticket_prices_error), onRefresh)
            }
            is TicketPricesUiState.Ready -> {
                val snapshot = state.snapshot
                val active = snapshot.origins.firstOrNull { it.city == selectedOrigin }
                    ?: snapshot.origins.first()

                item {
                    FareSummaryCard(
                        stale = snapshot.stale,
                        observedAt = snapshot.observedAt,
                        routeCount = active.fares.size,
                        onRefresh = onRefresh,
                    )
                }
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                        Text(
                            stringResource(R.string.ticket_prices_origin),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                        )
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
                }
                item {
                    OutlinedTextField(
                        value = search,
                        onValueChange = { search = it },
                        label = { Text(stringResource(R.string.ticket_prices_search)) },
                        leadingIcon = { Text("⌕", fontSize = 26.sp) },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        singleLine = true,
                    )
                }
                val fares = active.fares.filter {
                    it.destination.contains(search.trim(), ignoreCase = true)
                }.sortedBy { it.currentToman }
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            stringResource(R.string.ticket_prices_live_label),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            stringResource(R.string.ticket_prices_fares_count, fares.size),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            style = MaterialTheme.typography.labelMedium,
                        )
                    }
                }
                if (fares.isEmpty()) {
                    item { TravelEmptyState(stringResource(R.string.ticket_prices_empty)) }
                } else {
                    items(fares) { fare -> FareCard(fare) }
                }
                if (allowSupport) {
                    item {
                        Button(
                            onClick = onSupport,
                            modifier = Modifier.fillMaxWidth(),
                            contentPadding = PaddingValues(vertical = 14.dp),
                        ) {
                            Text(stringResource(R.string.ticket_prices_support), fontWeight = FontWeight.Bold)
                        }
                    }
                }
                item {
                    Text(
                        "قیمت‌های بلیت ممکن است تا هنگام رزرو تغییر کنند.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Start,
                    )
                }
            }
        }
    }
}

@Composable
private fun FareSummaryCard(
    stale: Boolean,
    observedAt: String,
    routeCount: Int,
    onRefresh: () -> Unit,
) {
    val timestamp = runCatching {
        OffsetDateTime.parse(observedAt)
            .atZoneSameInstant(ZoneId.of("Asia/Tehran"))
            .format(DateTimeFormatter.ofPattern("yyyy/MM/dd  HH:mm", Locale("fa", "IR")))
    }.getOrElse { observedAt.take(16).replace("T", " ") }

    Card(
        shape = RoundedCornerShape(21.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (stale) MaterialTheme.colorScheme.errorContainer
            else MaterialTheme.colorScheme.primaryContainer,
        ),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(11.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Surface(
                    color = MaterialTheme.colorScheme.surface,
                    shape = RoundedCornerShape(50),
                ) {
                    Text(
                        if (stale) stringResource(R.string.ticket_prices_outdated_label)
                        else stringResource(R.string.ticket_prices_live_label),
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = if (stale) MaterialTheme.colorScheme.error
                        else MaterialTheme.colorScheme.primary,
                    )
                }
                Text(
                    stringResource(R.string.ticket_prices_fares_count, routeCount),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
            Text(
                stringResource(R.string.ticket_prices_observed, timestamp),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface,
            )
            if (stale) {
                Text(
                    stringResource(R.string.ticket_prices_stale),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
            TextButton(onClick = onRefresh) {
                Text("↻  " + stringResource(R.string.ticket_prices_refresh))
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
        percent < 0 -> MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.error
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.6f)),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    fare.destination,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                val change = when {
                    percent == null -> "بدون مقایسه"
                    percent < -0.05 -> "↓ " + number.format(abs(percent)) + "٪"
                    percent > 0.05 -> "↑ " + number.format(percent) + "٪"
                    else -> "بدون تغییر"
                }
                Surface(
                    color = if (percent == null || abs(percent) < 0.05)
                        MaterialTheme.colorScheme.surfaceVariant
                    else if (percent < 0) MaterialTheme.colorScheme.primaryContainer
                    else MaterialTheme.colorScheme.errorContainer,
                    shape = RoundedCornerShape(9.dp),
                ) {
                    Text(
                        change,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        color = changeColor,
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }

            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    number.format(fare.currentToman),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Text(
                    "  تومان",
                    modifier = Modifier.padding(bottom = 3.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    stringResource(R.string.ticket_prices_average),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    fare.averageToman?.let {
                        stringResource(R.string.ticket_prices_toman, number.format(it))
                    } ?: stringResource(R.string.ticket_prices_no_average),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
