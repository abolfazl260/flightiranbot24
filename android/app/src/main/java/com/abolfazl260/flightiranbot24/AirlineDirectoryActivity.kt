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
import kotlinx.coroutines.CancellationException

/** Read-only GitHub guides. No login, submissions, web scraping or rating inference. */
class AirlineDirectoryActivity : ComponentActivity() {
    override fun attachBaseContext(newBase: Context) = super.attachBaseContext(PersianContext.wrap(newBase))

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TravelTheme {
                val repository = remember { AirlineContentRepository(applicationContext) }
                var index by remember { mutableStateOf<List<AirlineReference>?>(null) }
                var page by remember { mutableStateOf<AirlinePage?>(null) }
                var selected by rememberSaveable { mutableStateOf<String?>(null) }
                var section by rememberSaveable { mutableStateOf<String?>(null) }
                var loading by remember { mutableStateOf(true) }
                var error by remember { mutableStateOf(false) }
                var indexOffline by remember { mutableStateOf(false) }
                var detailOffline by remember { mutableStateOf(false) }
                var refresh by remember { mutableIntStateOf(0) }
                LaunchedEffect(selected, refresh) {
                    loading = true
                    error = false
                    page = null
                    try {
                        // Refresh identity/publication before fetching detail. Archived entries
                        // returned successfully by the server never fall back to bundled pages.
                        val result = repository.index()
                        index = result.value
                        indexOffline = result.usedBundledFallback
                        val reference = result.value.firstOrNull { it.id == selected }
                        if (reference != null) {
                            val detail = repository.detail(reference)
                            page = detail.value
                            detailOffline = detail.usedBundledFallback
                        }
                    } catch (cancel: CancellationException) {
                        throw cancel
                    } catch (_: Exception) {
                        error = true
                    } finally {
                        loading = false
                    }
                }
                val back: () -> Unit = {
                    if (section != null) section = null
                    else if (selected != null) selected = null
                    else finish()
                }
                BackHandler(selected != null, onBack = back)
                AirlineGuideScreen(
                    index = index, page = page, selected = selected, sectionId = section,
                    loading = loading, error = error,
                    offline = indexOffline || (selected != null && detailOffline),
                    onSelect = { selected = it; section = null }, onSection = { section = it },
                    onBack = back, onRetry = { refresh++ }, onLink = ::openHttps,
                    onAirport = {
                        startActivity(Intent(this, AirportDirectoryActivity::class.java)
                            .putExtra("airport_iata", it))
                    },
                    onShare = { reference ->
                        try {
                            startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
                                type = "text/plain"
                                putExtra(Intent.EXTRA_TEXT, reference.name + "\n" + reference.website)
                            }, "اشتراک‌گذاری ایرلاین"))
                        } catch (_: ActivityNotFoundException) { unavailable() }
                    },
                    onHome = { mainTab(TravelTab.HOME) },
                    onServices = { mainTab(TravelTab.SERVICES) },
                    onPrices = { startActivity(Intent(this, TicketPricesActivity::class.java)) },
                    onChecklist = { startActivity(Intent(this, ChecklistActivity::class.java)) },
                )
            }
        }
    }

    private fun mainTab(tab: TravelTab) {
        startActivity(Intent(this, MainActivity::class.java).putExtra(MainActivity.EXTRA_TAB, tab.name)
            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP))
        finish()
    }
    private fun openHttps(url: String) {
        if (runCatching { AirlineContentParser.https(url) }.isFailure) return
        try { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
        catch (_: ActivityNotFoundException) { unavailable() }
    }
    private fun unavailable() = Toast.makeText(this, R.string.link_unavailable, Toast.LENGTH_LONG).show()
}
