package com.abolfazl260.flightiranbot24

import android.content.Context
import android.os.Bundle
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
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.abolfazl260.flightiranbot24.data.fids.FlightDirection
import com.abolfazl260.flightiranbot24.data.fids.IranFidsBoard
import com.abolfazl260.flightiranbot24.data.fids.IranFlight
import com.abolfazl260.flightiranbot24.data.fids.iranFidsAirports
import com.abolfazl260.flightiranbot24.di.AppContainer
import com.abolfazl260.flightiranbot24.presentation.components.TravelEmptyState
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelToolbar
import com.abolfazl260.flightiranbot24.presentation.fids.IranFidsUiState
import com.abolfazl260.flightiranbot24.presentation.fids.IranFidsViewModel
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Native flight board: neither WebView nor external browser is used. */
class IranFlightsActivity : ComponentActivity() {
    private val container by lazy { AppContainer(applicationContext) }

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val model: IranFidsViewModel = viewModel(factory = container.iranFidsViewModelFactory)
            val state by model.state.collectAsStateWithLifecycle()
            val airport by model.selectedAirport.collectAsStateWithLifecycle()
            val direction by model.selectedDirection.collectAsStateWithLifecycle()
            TravelTheme {
                IranFlightsScreen(
                    state = state,
                    selectedAirport = airport,
                    selectedDirection = direction,
                    onAirport = model::selectAirport,
                    onDirection = model::selectDirection,
                    onRefresh = model::refresh,
                    onBack = ::finish
                )
            }
        }
    }
}

@Composable
internal fun IranFlightsScreen(
    state: IranFidsUiState,
    selectedAirport: String,
    selectedDirection: FlightDirection,
    onAirport: (String) -> Unit,
    onDirection: (FlightDirection) -> Unit,
    onRefresh: () -> Unit,
    onBack: () -> Unit
) {
    var search by rememberSaveable { mutableStateOf("") }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            TravelToolbar(title = stringResource(R.string.iran_fids_title), onBack = onBack)
            Text(
                "اطلاعات از منبع رسمی FIDS درخواست می‌شود و در خود برنامه نمایش داده خواهد شد؛ " +
                    "وضعیت پرواز را پیش از مراجعه با فرودگاه یا شرکت هواپیمایی تأیید کنید.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        item {
            Text("فرودگاه", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(iranFidsAirports, key = { it.code }) { airport ->
                    FilterChip(
                        selected = selectedAirport == airport.code,
                        onClick = { search = ""; onAirport(airport.code) },
                        label = { Text(airport.name + " · " + airport.code) }
                    )
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                FlightDirection.entries.forEach { option ->
                    FilterChip(
                        selected = selectedDirection == option,
                        onClick = { search = ""; onDirection(option) },
                        label = { Text("پروازهای " + option.label) }
                    )
                }
            }
        }
        item {
            OutlinedTextField(
                value = search,
                onValueChange = { search = it },
                label = { Text("جست‌وجوی شماره پرواز، مسیر یا ایرلاین") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
        }
        when (state) {
            IranFidsUiState.Loading -> item {
                TravelLoadingState("در حال دریافت اطلاعات پرواز از منبع رسمی…")
            }
            IranFidsUiState.Unavailable -> item {
                TravelErrorState(
                    "در حال حاضر اطلاعات معتبر FIDS برای این فرودگاه در دسترس نیست. " +
                        "ممکن است اتصال رسمی سامانه یا فرودگاه هنوز تأیید نشده باشد.",
                    onRefresh
                )
            }
            is IranFidsUiState.Ready -> {
                val board = state.board
                item { FidsSourceCard(board, onRefresh) }
                val q = search.trim().lowercase(Locale.ROOT)
                val visible = board.flights.filter { flight ->
                    q.isEmpty() ||
                        flight.flightNumber.lowercase(Locale.ROOT).contains(q) ||
                        flight.city.lowercase(Locale.ROOT).contains(q) ||
                        flight.airline.orEmpty().lowercase(Locale.ROOT).contains(q)
                }
                item {
                    Text(
                        "پروازهای " + selectedDirection.label + " · " + visible.size + " مورد",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                }
                if (visible.isEmpty()) item {
                    TravelEmptyState(
                        if (q.isEmpty()) "پروازی در پاسخ منبع ثبت نشده است."
                        else "پروازی مطابق این جست‌وجو پیدا نشد."
                    )
                } else items(visible) { flight -> FidsFlightCard(flight) }
            }
        }
    }
}

@Composable
private fun FidsSourceCard(board: IranFidsBoard, onRefresh: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (board.sourceIsOld) MaterialTheme.colorScheme.errorContainer
            else MaterialTheme.colorScheme.primaryContainer
        ),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(7.dp)
        ) {
            Text("منبع: سامانه اطلاعات پرواز فرودگاه‌های کشور (FIDS)",
                style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
            Text("زمان دریافت توسط سامانه: " + iranFidsDate(board.fetchedAt),
                style = MaterialTheme.typography.bodySmall)
            Text(
                if (board.sourceUpdatedAt == null)
                    "زمان آخرین به‌روزرسانی اطلاعات توسط منبع اعلام نشده است."
                else "زمان اعلام‌شده توسط منبع: " + iranFidsDate(board.sourceUpdatedAt),
                style = MaterialTheme.typography.bodySmall
            )
            if (board.sourceIsOld) {
                Text("تازگی داده‌ها تأیید نشده است؛ اطلاعات ممکن است تغییر کرده باشند.",
                    style = MaterialTheme.typography.bodySmall)
            }
            TextButton(onClick = onRefresh) { Text("↻  دریافت مجدد اطلاعات") }
        }
    }
}

@Composable
private fun FidsFlightCard(flight: IranFlight) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.55f)),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(flight.flightNumber, style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold)
                Text(flight.status ?: "وضعیت اعلام نشده",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text(flight.city, style = MaterialTheme.typography.titleMedium)
            flight.airline?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
            Text("زمان برنامه‌ای: " + flight.scheduledTime,
                style = MaterialTheme.typography.bodyMedium)
            flight.estimatedTime?.let { Text("زمان تخمینی: " + it) }
            flight.actualTime?.let { Text("زمان واقعی: " + it) }
            flight.terminal?.let { Text("ترمینال: " + it) }
            flight.gate?.let { Text("گیت: " + it) }
        }
    }
}

private fun iranFidsDate(value: String): String =
    runCatching {
        OffsetDateTime.parse(value).atZoneSameInstant(ZoneId.of("Asia/Tehran"))
            .format(DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm", Locale("fa", "IR")))
    }.getOrElse { "نامشخص" }
