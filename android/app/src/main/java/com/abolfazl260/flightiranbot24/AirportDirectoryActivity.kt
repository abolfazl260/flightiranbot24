package com.abolfazl260.flightiranbot24

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import com.abolfazl260.flightiranbot24.presentation.components.TravelTab
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import com.google.gson.JsonParser
import java.net.URI
import java.util.Locale
import kotlinx.coroutines.CancellationException

/**
 * Read-only, Persian-only airport entry point. Publication state and all
 * section content come from GitHub JSON, never an administrator panel.
 */
class AirportDirectoryActivity : ComponentActivity() {
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TravelTheme {
                val repository = remember { AirportContentRepository(applicationContext) }
                val names = remember { readBundledAirportNames(applicationContext) }
                var index by remember { mutableStateOf<AirportContentIndex?>(null) }
                var indexLoading by remember { mutableStateOf(true) }
                var indexOffline by remember { mutableStateOf(false) }
                var indexError by remember { mutableStateOf(false) }
                var selectedCode by rememberSaveable { mutableStateOf<String?>(null) }
                var page by remember { mutableStateOf<AirportContentPage?>(null) }
                var detailLoading by remember { mutableStateOf(false) }
                var detailOffline by remember { mutableStateOf(false) }
                var detailError by remember { mutableStateOf(false) }
                var refreshKey by remember { mutableIntStateOf(0) }

                LaunchedEffect(repository, refreshKey) {
                    indexLoading = true
                    indexError = false
                    try {
                        val loaded = repository.index()
                        index = loaded.value
                        indexOffline = loaded.usedBundledFallback
                        if (selectedCode != null &&
                            loaded.value.airports.none { it.iata == selectedCode }
                        ) {
                            selectedCode = null
                            page = null
                        }
                    } catch (cancel: CancellationException) {
                        throw cancel
                    } catch (_: Exception) {
                        indexError = true
                    } finally {
                        indexLoading = false
                    }
                }

                LaunchedEffect(repository, index, selectedCode, refreshKey) {
                    page = null
                    detailError = false
                    if (selectedCode == null || index == null) {
                        detailLoading = false
                    } else {
                        val ref = index?.airports?.firstOrNull { it.iata == selectedCode }
                        if (ref == null) {
                            detailError = true
                            detailLoading = false
                        } else {
                            detailLoading = true
                            try {
                                val loaded = repository.detail(ref)
                                page = loaded.value
                                detailOffline = loaded.usedBundledFallback
                                if (loaded.value.sections.isEmpty()) detailError = true
                            } catch (cancel: CancellationException) {
                                throw cancel
                            } catch (_: Exception) {
                                detailError = true
                            } finally {
                                detailLoading = false
                            }
                        }
                    }
                }
                BackHandler(enabled = selectedCode != null) {
                    selectedCode = null
                }

                AirportGuideScreen(
                    index = index,
                    page = page,
                    airportNames = names,
                    selectedCode = selectedCode,
                    indexLoading = indexLoading,
                    detailLoading = detailLoading,
                    indexError = indexError,
                    detailError = detailError,
                    offline = if (selectedCode == null) indexOffline else detailOffline,
                    onSelectAirport = { selectedCode = it },
                    onBack = {
                        if (selectedCode != null) selectedCode = null else finish()
                    },
                    onRetry = { refreshKey++ },
                    onLink = ::openHttps,
                    onHome = { openMainTab(TravelTab.HOME) },
                    onPrices = {
                        startActivity(Intent(this, TicketPricesActivity::class.java))
                        finish()
                    },
                    onChecklist = {
                        startActivity(Intent(this, ChecklistActivity::class.java))
                        finish()
                    },
                    onServices = { openMainTab(TravelTab.SERVICES) },
                )
            }
        }
    }

    private fun openMainTab(tab: TravelTab) {
        startActivity(
            Intent(this, MainActivity::class.java)
                .putExtra(MainActivity.EXTRA_TAB, tab.name)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        )
        finish()
    }

    private fun openHttps(url: String) {
        val uri = runCatching { URI(url) }.getOrNull()
        if (uri?.scheme != "https" || uri.host.isNullOrBlank() || uri.rawUserInfo != null) return
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, R.string.link_unavailable, Toast.LENGTH_LONG).show()
        }
    }
}

internal fun readBundledAirportNames(context: Context): Map<String, AirportRow> = runCatching {
    val json = context.assets.open("airports.json").bufferedReader().use { it.readText() }
    JsonParser.parseString(json).asJsonArray.associate { element ->
        val record = element.asJsonObject
        val names = record.getAsJsonObject("names")
        val code = record.get("code").asString
        code to AirportRow(
            code = code,
            name = names.get("fa").asString,
            country = record.get("country").asString,
            timezone = record.get("timezone").asString,
            aliases = listOfNotNull(names.get("en")?.asString, names.get("ar")?.asString),
        )
    }
}.getOrDefault(emptyMap())

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
