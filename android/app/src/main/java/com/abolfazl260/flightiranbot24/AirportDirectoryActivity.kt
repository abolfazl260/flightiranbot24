package com.abolfazl260.flightiranbot24

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.abolfazl260.flightiranbot24.di.AppContainer
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import com.abolfazl260.flightiranbot24.presentation.components.TravelToolbar
import com.abolfazl260.flightiranbot24.presentation.components.TravelFormField
import com.abolfazl260.flightiranbot24.presentation.components.TravelListRow
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelEmptyState
import androidx.compose.ui.res.stringResource
import java.util.Locale
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray

/** Offline-first airport list: prefer a valid local Room snapshot, otherwise packaged data. */
class AirportDirectoryActivity : ComponentActivity() {
    private val container by lazy { AppContainer(applicationContext) }

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            var rows by remember { mutableStateOf<List<AirportRow>>(emptyList()) }
            var source by remember { mutableStateOf("") }
            var error by remember { mutableStateOf(false) }
            var loading by remember { mutableStateOf(true) }
            LaunchedEffect(Unit) {
                try {
                    val result = withContext(Dispatchers.IO) { loadOfflineCatalog() }
                    rows = result.first
                    source = result.second
                } catch (_: Exception) {
                    error = true
                } finally {
                    loading = false
                }
            }
            TravelTheme {
                AirportDirectoryScreen(
                    rows = rows, source = source, loading = loading, error = error,
                    onBack = { finish() },
                )
            }
        }
    }

    private suspend fun loadOfflineCatalog(): Pair<List<AirportRow>, String> {
        // If Room cannot be opened, the packaged list remains usable offline.
        val cached = try {
            container.airportCacheRepository.all()
        } catch (_: Exception) {
            emptyList()
        }
        if (cached.isNotEmpty()) {
            return cached.map { airport ->
                AirportRow(airport.iata, airport.name, airport.country, airport.timezone)
            } to "ذخیره آفلاین دستگاه"
        }
        val source = assets.open("airports.json").bufferedReader(Charsets.UTF_8).use {
            it.readText()
        }
        val items = JSONArray(source)
        val rows = buildList {
            for (i in 0 until items.length()) {
                val obj = items.getJSONObject(i)
                val names = obj.getJSONObject("names")
                add(
                    AirportRow(
                        code = obj.getString("code"),
                        name = names.optString("fa").ifBlank { names.getString("en") },
                        country = obj.getString("country"),
                        timezone = obj.getString("timezone"),
                        aliases = listOf(names.optString("en"), names.optString("ar")),
                    )
                )
            }
        }
        return rows to "فهرست همراه برنامه"
    }
}

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
    return rows.filter { item ->
        listOf(item.code, item.name, item.country, item.timezone, *item.aliases.toTypedArray())
            .any { it.normalizedSearch().contains(query) }
    }.sortedBy { it.name }
}

@Composable
internal fun AirportDirectoryScreen(
    rows: List<AirportRow>,
    source: String,
    loading: Boolean,
    error: Boolean,
    onBack: () -> Unit,
) {
    var search by rememberSaveable { mutableStateOf("") }
    var expandedCode by rememberSaveable { mutableStateOf<String?>(null) }
    val filtered = remember(rows, search) { filterAirports(rows, search) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(androidx.compose.foundation.layout.WindowInsets.safeDrawing)
            .padding(horizontal = 18.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        TravelToolbar(title = "فرودگاه‌ها", onBack = onBack)
        Text(
            "جست‌وجوی آفلاین با نام فرودگاه، شهر یا کد IATA",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            style = MaterialTheme.typography.bodyMedium,
        )
        TravelFormField(
            value = search,
            onValueChange = { search = it },
            label = stringResource(R.string.search_airports),
        )
        if (loading) {
            TravelLoadingState()
        } else if (error) {
            TravelErrorState(stringResource(R.string.airports_unavailable))
        } else {
            Text(
                "${filtered.size} فرودگاه از ${rows.size} · $source",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
            )
            if (filtered.isEmpty()) {
                TravelEmptyState(stringResource(R.string.no_airports))
            }
            LazyColumn(
                modifier = Modifier.fillMaxWidth(),
                contentPadding = PaddingValues(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                items(filtered, key = { it.code }) { airport ->
                    TravelListRow(
                        title = airport.name,
                        subtitle = "${airport.code} · ${airport.country}",
                        details = "منطقه زمانی: ${airport.timezone}",
                        expanded = expandedCode == airport.code,
                        onClick = {
                            expandedCode = if (expandedCode == airport.code) null else airport.code
                        },
                    )
                }
            }
        }
    }
}
