package com.abolfazl260.flightiranbot24

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.abolfazl260.flightiranbot24.presentation.components.TravelBottomNavigation
import com.abolfazl260.flightiranbot24.presentation.components.TravelEmptyState
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelTab
import com.abolfazl260.flightiranbot24.presentation.components.TravelToolbar
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Native Persian travel directory; Telegram is not needed to browse its entries. */
class TravelWebsitesActivity : ComponentActivity() {
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TravelTheme {
                val context = LocalContext.current.applicationContext
                val repository = remember(context) { TravelWebsiteCatalogRepository(context) }
                var catalog by remember { mutableStateOf<TravelWebsiteCatalog?>(null) }
                var loading by remember { mutableStateOf(true) }
                var offline by remember { mutableStateOf(false) }
                var refreshKey by remember { mutableIntStateOf(0) }

                LaunchedEffect(repository, refreshKey) {
                    loading = true
                    offline = false
                    if (catalog == null) {
                        try {
                            catalog = repository.bundled()
                        } catch (e: CancellationException) {
                            throw e
                        } catch (_: Exception) {
                            // A live catalog can still recover an unavailable bundled copy.
                        }
                    }
                    try {
                        catalog = repository.latest()
                    } catch (e: CancellationException) {
                        throw e
                    } catch (_: Exception) {
                        offline = true
                    }
                    loading = false
                }

                TravelWebsitesScreen(
                    catalog = catalog,
                    loading = loading,
                    offline = offline,
                    onRefresh = { refreshKey++ },
                    onBack = ::finish,
                    onOpenWebsite = ::openWebsite,
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

    private fun openWebsite(url: String) {
        if (Uri.parse(url).scheme != "https") return
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, R.string.link_unavailable, Toast.LENGTH_LONG).show()
        }
    }
}

@Composable
internal fun TravelWebsitesScreen(
    catalog: TravelWebsiteCatalog?,
    loading: Boolean,
    offline: Boolean,
    onRefresh: () -> Unit,
    onBack: () -> Unit,
    onOpenWebsite: (String) -> Unit,
    onHome: () -> Unit = onBack,
    onPrices: () -> Unit = {},
    onChecklist: () -> Unit = {},
    onServices: () -> Unit = {},
) {
    var search by rememberSaveable { mutableStateOf("") }
    var categoryId by rememberSaveable { mutableStateOf("") }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            TravelBottomNavigation(
                selectedTab = TravelTab.SERVICES,
                onHome = onHome,
                onPrices = onPrices,
                onChecklist = onChecklist,
                onServices = onServices,
            )
        },
    ) { insets ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(insets),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                TravelToolbar(
                    title = stringResource(R.string.travel_websites_title),
                    onBack = onBack,
                )
            }
            item {
                Text(
                    stringResource(R.string.travel_websites_intro),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        stringResource(R.string.travel_websites_count, catalog?.websites?.size ?: 0),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    TextButton(onClick = onRefresh, enabled = !loading) {
                        Text(stringResource(R.string.travel_websites_refresh))
                    }
                }
            }
            if (loading) {
                item { LinearProgressIndicator(modifier = Modifier.fillMaxWidth()) }
            }
            if (offline && catalog != null) {
                item {
                    Text(
                        stringResource(R.string.travel_websites_offline),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            if (catalog == null) {
                item {
                    if (loading) {
                        TravelLoadingState()
                    } else {
                        TravelErrorState(stringResource(R.string.travel_websites_error), onRefresh)
                    }
                }
            } else {
                val availableCategories = catalog.categories.filter { category ->
                    catalog.websites.any { it.categoryId == category.id }
                }
                item {
                    OutlinedTextField(
                        value = search,
                        onValueChange = { search = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        shape = RoundedCornerShape(15.dp),
                        label = { Text(stringResource(R.string.travel_websites_search)) },
                    )
                }
                item {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        item {
                            FilterChip(
                                selected = categoryId.isEmpty(),
                                onClick = { categoryId = "" },
                                label = { Text(stringResource(R.string.travel_websites_all)) },
                            )
                        }
                        items(availableCategories, key = { it.id }) { category ->
                            FilterChip(
                                selected = categoryId == category.id,
                                onClick = { categoryId = category.id },
                                label = { Text(category.title) },
                            )
                        }
                    }
                }
                val query = search.trim()
                val visible = catalog.websites.filter { item ->
                    (categoryId.isEmpty() || categoryId == item.categoryId) &&
                        (query.isEmpty() ||
                            item.title.contains(query, ignoreCase = true) ||
                            item.description.contains(query, ignoreCase = true))
                }
                if (visible.isEmpty()) {
                    item { TravelEmptyState(stringResource(R.string.travel_websites_empty)) }
                } else {
                    val names = catalog.categories.associate { it.id to it.title }
                    items(visible, key = { it.id }) { website ->
                        TravelWebsiteCard(
                            website = website,
                            categoryTitle = names[website.categoryId].orEmpty(),
                            onOpen = { onOpenWebsite(website.url) },
                        )
                    }
                }
                item {
                    Text(
                        stringResource(R.string.travel_websites_disclaimer),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun TravelWebsiteCard(
    website: TravelWebsite,
    categoryTitle: String,
    onOpen: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        onClick = onOpen,
        shape = RoundedCornerShape(19.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.45f)),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(15.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                TravelWebsiteThumbnail(website.imagePath)
                Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text(
                        website.title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        categoryTitle,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }
            Text(
                website.description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                stringResource(R.string.travel_websites_open),
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.SemiBold,
                style = MaterialTheme.typography.labelLarge,
            )
        }
    }
}

@Composable
private fun TravelWebsiteThumbnail(imagePath: String) {
    val context = LocalContext.current.applicationContext
    val thumbnail by produceState<ImageBitmap?>(initialValue = null, key1 = imagePath) {
        value = withContext(Dispatchers.IO) {
            try {
                context.assets.open(imagePath).use { BitmapFactory.decodeStream(it)?.asImageBitmap() }
            } catch (_: Exception) {
                null
            }
        }
    }
    val shape = RoundedCornerShape(13.dp)
    if (thumbnail != null) {
        Image(
            bitmap = thumbnail!!,
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier.size(70.dp).clip(shape),
        )
    } else {
        Box(
            modifier = Modifier.size(70.dp).clip(shape)
                .background(MaterialTheme.colorScheme.primaryContainer),
        )
    }
}
