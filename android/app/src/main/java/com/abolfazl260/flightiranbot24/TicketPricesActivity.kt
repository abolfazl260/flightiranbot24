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
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.runtime.remember
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.abolfazl260.flightiranbot24.data.tickets.TicketFare
import com.abolfazl260.flightiranbot24.di.AppContainer
import com.abolfazl260.flightiranbot24.presentation.components.TravelEmptyState
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelBottomNavigation
import com.abolfazl260.flightiranbot24.presentation.components.TravelTab
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
                    onHome = { openMainTab(TravelTab.HOME) },
                    onChecklist = { startActivity(Intent(this, ChecklistActivity::class.java)) },
                    onServices = { openMainTab(TravelTab.SERVICES) },
                    onRefresh = model::refresh,
                    onSupport = { openUrl(BotLinks.SUPPORT) },
                    allowSupport = true,
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
    onHome: () -> Unit = onBack,
    onChecklist: () -> Unit = {},
    onServices: () -> Unit = {},
) {
    var selectedOrigin by rememberSaveable { mutableStateOf("") }
    var search by rememberSaveable { mutableStateOf("") }
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        // Deliberately keep the app-wide footer and its navigation unchanged.
        bottomBar = {
            TravelBottomNavigation(
                selectedTab = TravelTab.PRICES,
                onHome = onHome,
                onPrices = {},
                onChecklist = onChecklist,
                onServices = onServices,
            )
        },
    ) { scaffoldPadding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(scaffoldPadding),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                TicketPricesHeader(onBack = onBack)
            }
            when (state) {
                TicketPricesUiState.Loading -> item {
                    TravelLoadingState("در حال دریافت قیمت‌های ثبت‌شده…")
                }
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
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                stringResource(R.string.ticket_prices_origin),
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                            )
                            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                items(snapshot.origins, key = { it.city }) { route ->
                                    FilterChip(
                                        selected = route.city == active.city,
                                        onClick = {
                                            selectedOrigin = route.city
                                            search = ""
                                        },
                                        label = {
                                            Text(
                                                "از " + route.city,
                                                fontWeight = if (route.city == active.city)
                                                    FontWeight.Bold else FontWeight.Medium,
                                            )
                                        },
                                        shape = RoundedCornerShape(16.dp),
                                        colors = FilterChipDefaults.filterChipColors(
                                            selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                            selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                                        ),
                                    )
                                }
                            }
                        }
                    }
                    item {
                        OutlinedTextField(
                            value = search,
                            onValueChange = { search = it },
                            placeholder = { Text(stringResource(R.string.ticket_prices_search)) },
                            leadingIcon = {
                                Text(
                                    "⌕",
                                    fontSize = 26.sp,
                                    color = MaterialTheme.colorScheme.primary,
                                )
                            },
                            trailingIcon = if (search.isNotEmpty()) {
                                {
                                    TextButton(onClick = { search = "" }) {
                                        Text("پاک‌کردن")
                                    }
                                }
                            } else null,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(18.dp),
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
                            Surface(
                                color = MaterialTheme.colorScheme.primaryContainer,
                                shape = RoundedCornerShape(50),
                            ) {
                                Text(
                                    stringResource(R.string.ticket_prices_fares_count, fares.size),
                                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 5.dp),
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                                )
                            }
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
                                Text(
                                    stringResource(R.string.ticket_prices_support),
                                    fontWeight = FontWeight.Bold,
                                )
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
}

@Composable
private fun TicketPricesHeader(onBack: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Surface(
                    color = MaterialTheme.colorScheme.primary,
                    shape = RoundedCornerShape(14.dp),
                ) {
                    Text(
                        "✈",
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                        color = MaterialTheme.colorScheme.onPrimary,
                        fontSize = 24.sp,
                    )
                }
                Text(
                    stringResource(R.string.ticket_prices_title),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                )
            }
            TextButton(
                onClick = onBack,
                modifier = Modifier.heightIn(min = 48.dp),
            ) {
                Text("بازگشت")
            }
        }
        Text(
            stringResource(R.string.ticket_prices_explanation),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            style = MaterialTheme.typography.bodySmall,
        )
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

    val backgroundColors = if (stale) {
        listOf(MaterialTheme.colorScheme.errorContainer, MaterialTheme.colorScheme.surfaceVariant)
    } else {
        listOf(MaterialTheme.colorScheme.primaryContainer, MaterialTheme.colorScheme.surfaceVariant)
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(24.dp))
            .background(Brush.horizontalGradient(backgroundColors))
            .padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(13.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shape = RoundedCornerShape(50),
            ) {
                Text(
                    if (stale) stringResource(R.string.ticket_prices_outdated_label)
                    else stringResource(R.string.ticket_prices_live_label),
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = if (stale) MaterialTheme.colorScheme.error
                    else MaterialTheme.colorScheme.primary,
                )
            }
            Text(
                "✈  " + stringResource(R.string.ticket_prices_fares_count, routeCount),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.SemiBold,
            )
        }
        Text(
            stringResource(R.string.ticket_prices_observed, timestamp),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            TextButton(
                onClick = onRefresh,
                modifier = Modifier.heightIn(min = 48.dp),
            ) {
                Text(
                    "↻  " + stringResource(R.string.ticket_prices_refresh),
                    fontWeight = FontWeight.Bold,
                )
            }
            Text(
                if (stale) stringResource(R.string.ticket_prices_stale)
                else "بر اساس آخرین دادهٔ ثبت‌شده",
                style = MaterialTheme.typography.labelSmall,
                color = if (stale) MaterialTheme.colorScheme.error
                else MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/** A compact three-part fare row, with a high-font-scale layout for readability. */
@Composable
private fun FareCard(fare: TicketFare) {
    val number = NumberFormat.getNumberInstance(Locale("fa", "IR"))
    val percent = fare.differencePercent
    val change = when {
        percent == null -> "بدون مقایسه"
        percent < -0.05 -> "↓ " + number.format(abs(percent)) + "٪"
        percent > 0.05 -> "↑ " + number.format(percent) + "٪"
        else -> "بدون تغییر"
    }
    val changeColor = when {
        percent == null || abs(percent) <= 0.05 -> MaterialTheme.colorScheme.onSurfaceVariant
        percent < 0 -> MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.error
    }
    val badgeBackground = when {
        percent == null || abs(percent) <= 0.05 -> MaterialTheme.colorScheme.surfaceVariant
        percent < 0 -> MaterialTheme.colorScheme.primaryContainer
        else -> MaterialTheme.colorScheme.errorContainer
    }
    val average = fare.averageToman?.let { "میانگین: " + number.format(it) }
        ?: stringResource(R.string.ticket_prices_no_average)
    val largeType = LocalDensity.current.fontScale >= 1.4f

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.48f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        if (largeType) {
            Column(
                modifier = Modifier.fillMaxWidth().padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Row(
                        modifier = Modifier.weight(1f),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        FareCityIcon(city = fare.destination, size = 38.dp)
                        Text(
                            fare.destination,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    FareChangeBadge(change, changeColor, badgeBackground)
                }
                Text(
                    number.format(fare.currentToman) + " تومان",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    if (fare.averageToman != null) average + " تومان" else average,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        } else {
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Row(
                    modifier = Modifier.weight(1.05f),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    FareCityIcon(city = fare.destination, size = 38.dp)
                    Text(
                        fare.destination,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Column(
                    modifier = Modifier.weight(1.25f),
                    verticalArrangement = Arrangement.spacedBy(3.dp),
                ) {
                    Text(
                        number.format(fare.currentToman),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        "تومان",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.labelSmall,
                    )
                    Text(
                        average,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.labelSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                FareChangeBadge(change, changeColor, badgeBackground)
            }
        }
    }
}

@Composable
private fun FareChangeBadge(
    label: String,
    color: androidx.compose.ui.graphics.Color,
    background: androidx.compose.ui.graphics.Color,
) {
    Surface(color = background, shape = RoundedCornerShape(12.dp)) {
        Text(
            label,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 8.dp),
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            color = color,
            maxLines = 1,
        )
    }
}

/**
 * One resource per city, shared by origin chips and destination fare cards.
 * When the corresponding drawable-nodpi WebP asset has not been installed yet,
 * it is deliberately omitted rather than showing a broken placeholder.
 */
@Composable
private fun FareCityIcon(city: String, size: Dp) {
    val resourceName = fareCityIconName(city) ?: return
    val context = LocalContext.current
    val drawableId = remember(context, resourceName) {
        @Suppress("DiscouragedApi")
        context.resources.getIdentifier(resourceName, "drawable", context.packageName)
    }
    if (drawableId != 0) {
        Image(
            painter = painterResource(drawableId),
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier.size(size),
        )
    }
}

internal fun fareCityIconName(city: String): String? {
    val normalized = city.trim()
        .replace('ي', 'ی')
        .replace('ك', 'ک')
        .replace(" ", "")
        .replace("‌", "")

    return when (normalized) {
        "مشهد" -> "price_city_mashhad"
        "استانبول" -> "price_city_istanbul"
        "نجف" -> "price_city_najaf"
        "شیراز" -> "price_city_shiraz"
        "اهواز" -> "price_city_ahvaz"
        "کیش" -> "price_city_kish"
        "تبریز" -> "price_city_tabriz"
        "کرمان" -> "price_city_kerman"
        "ایروان" -> "price_city_yerevan"
        "بندرعباس" -> "price_city_bandarabbas"
        "زاهدان" -> "price_city_zahedan"
        "ارومیه" -> "price_city_urmia"
        "آبادان" -> "price_city_abadan"
        "عسلویه" -> "price_city_assaluyeh"
        "بوشهر" -> "price_city_bushehr"
        "یزد" -> "price_city_yazd"
        "کرمانشاه" -> "price_city_kermanshah"
        "گوانجو" -> "price_city_guangzhou"
        "مسکو(شرمتیوو)", "مسکوشرمتیوو" -> "price_city_moscow_sheremetyevo"
        "قشم" -> "price_city_qeshm"
        "تهران" -> "price_city_tehran"
        "اصفهان" -> "price_city_isfahan"
        "رشت" -> "price_city_rasht"
        "همدان" -> "price_city_hamedan"
        "قم" -> "price_city_qom"
        "گرگان" -> "price_city_gorgan"
        "دبی" -> "price_city_dubai"
        "دوحه" -> "price_city_doha"
        "آنکارا" -> "price_city_ankara"
        "آنتالیا" -> "price_city_antalya"
        "سنندج" -> "price_city_sanandaj"
        "ساری" -> "price_city_sari"
        "اردبیل" -> "price_city_ardabil"
        "کاشان" -> "price_city_kashan"
        "خرمآباد" -> "price_city_khorramabad"
        "زنجان" -> "price_city_zanjan"
        "اراک" -> "price_city_arak"
        "یاسوج" -> "price_city_yasuj"
        "چابهار" -> "price_city_chabahar"
        "بندرانزلی" -> "price_city_bandaranzali"
        "سیرجان" -> "price_city_sirjan"
        "شانگهای" -> "price_city_shanghai"
        "بیرجند" -> "price_city_birjand"
        "کابل" -> "price_city_kabul"
        "ایلام" -> "price_city_ilam"
        "مزارشریف" -> "price_city_mazar_sharif"
        "بانکوک" -> "price_city_bangkok"
        "آلانیا" -> "price_city_alanya"
        "پکن" -> "price_city_beijing"
        "جیروفت" -> "price_city_jiroft"
        "بجنورد" -> "price_city_bojnord"
        "ماهشهر" -> "price_city_mahshahr"
        "رفسنجان" -> "price_city_rafsanjan"
        "طبس" -> "price_city_tabas"
        "لار" -> "price_city_lar"
        "سراوان" -> "price_city_saravan"
        else -> null
    }
}
