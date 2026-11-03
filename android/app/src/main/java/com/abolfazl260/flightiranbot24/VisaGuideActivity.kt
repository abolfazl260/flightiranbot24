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
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.abolfazl260.flightiranbot24.data.visa.VisaCountries
import com.abolfazl260.flightiranbot24.data.visa.VisaFailure
import com.abolfazl260.flightiranbot24.data.visa.VisaRule
import com.abolfazl260.flightiranbot24.data.visa.VisaStatus
import com.abolfazl260.flightiranbot24.di.AppContainer
import com.abolfazl260.flightiranbot24.presentation.components.TravelBottomNavigation
import com.abolfazl260.flightiranbot24.presentation.components.TravelEmptyState
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelTab
import com.abolfazl260.flightiranbot24.presentation.components.TravelToolbar
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import com.abolfazl260.flightiranbot24.presentation.visa.VisaGuideState
import com.abolfazl260.flightiranbot24.presentation.visa.VisaGuideViewModel
import com.abolfazl260.flightiranbot24.presentation.visa.VisaLoad

/** Native, public, read-only visa browsing; Telegram is an explicit alert-only handoff. */
class VisaGuideActivity : ComponentActivity() {
    private val container by lazy { AppContainer(applicationContext) }

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val model: VisaGuideViewModel = viewModel(factory = container.visaGuideViewModelFactory)
            val state by model.state.collectAsStateWithLifecycle()
            TravelTheme {
                BackHandler(enabled = state.selectedDestination != null) {
                    model.backToCountries()
                }
                VisaGuideScreen(
                    state = state,
                    onBack = {
                        if (!model.backToCountries()) finish()
                    },
                    onPassport = model::choosePassport,
                    onDestination = model::openDestination,
                    onRetryCatalog = model::retryCatalog,
                    onRetryDetail = model::retryDetail,
                    onSource = ::openHttpsSource,
                    onAlert = { passport, destination ->
                        openUrl(BotLinks.visaWatch(passport, destination))
                    },
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

    private fun openHttpsSource(url: String) {
        if (com.abolfazl260.flightiranbot24.data.visa.VisaRepository.safeSource(url) == null) {
            Toast.makeText(this, "پیوند منبع معتبر نیست.", Toast.LENGTH_LONG).show()
            return
        }
        openUrl(url)
    }

    private fun openUrl(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "برنامه‌ای برای باز کردن این پیوند پیدا نشد.", Toast.LENGTH_LONG).show()
        } catch (_: SecurityException) {
            Toast.makeText(this, "امکان باز کردن پیوند وجود ندارد.", Toast.LENGTH_LONG).show()
        }
    }
}

@Composable
internal fun VisaGuideScreen(
    state: VisaGuideState,
    onBack: () -> Unit,
    onPassport: (String) -> Unit,
    onDestination: (String) -> Unit,
    onRetryCatalog: () -> Unit,
    onRetryDetail: () -> Unit,
    onSource: (String) -> Unit,
    onAlert: (String, String) -> Unit,
    onHome: () -> Unit = onBack,
    onPrices: () -> Unit = {},
    onChecklist: () -> Unit = {},
    onServices: () -> Unit = {},
) {
    var search by rememberSaveable { mutableStateOf("") }
    var showPassports by rememberSaveable { mutableStateOf(false) }
    if (showPassports) {
        VisaPassportDialog(
            selected = state.passport,
            supportedCodes = state.passportCodes,
            onSelect = { country ->
                onPassport(country)
                search = ""
                showPassports = false
            },
            onClose = { showPassports = false },
        )
    }
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
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                TravelToolbar(
                    title = if (state.selectedDestination == null) "راهنمای ویزای کشورها" else "جزئیات ویزا",
                    onBack = onBack,
                )
            }
            if (state.selectedDestination == null) {
                item { VisaHero("راهنمای ویزای کشورها", "بررسی وضعیت ویزا، شرایط ورود و اقامت") }
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(20.dp),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)),
                    ) {
                        Column(
                            modifier = Modifier.fillMaxWidth().padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Text("کشور صادرکننده پاسپورت", fontWeight = FontWeight.Bold)
                            OutlinedButton(
                                onClick = { showPassports = true },
                                modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp),
                                shape = RoundedCornerShape(14.dp),
                            ) {
                                Text(VisaCountries.flag(state.passport) + "  " +
                                    VisaCountries.name(state.passport) + "  (" + state.passport + ")  ▾")
                            }
                            OutlinedTextField(
                                value = search,
                                onValueChange = { search = it },
                                label = { Text("کشور مقصد") },
                                placeholder = { Text("جست‌وجوی کشور مقصد…") },
                                leadingIcon = { Text("⌕") },
                                trailingIcon = {
                                    if (search.isNotBlank()) {
                                        TextButton(onClick = { search = "" }) { Text("پاک‌کردن") }
                                    }
                                },
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true,
                                shape = RoundedCornerShape(15.dp),
                            )
                        }
                    }
                }
                if (search.isBlank()) {
                    item {
                        Text("مقاصد پرطرفدار", style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold)
                    }
                    item {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            VisaCountries.popular.chunked(3).forEach { row ->
                                Row(modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                    row.forEach { code ->
                                        VisaDestinationCard(
                                            code = code,
                                            onClick = { onDestination(code) },
                                            modifier = Modifier.weight(1f),
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
                when (val result = state.catalog) {
                    VisaLoad.Loading -> item { TravelLoadingState("در حال آماده‌سازی اطلاعات آفلاین…") }
                    VisaLoad.Idle -> item { TravelLoadingState() }
                    is VisaLoad.Error -> item {
                        TravelErrorState(visaErrorText(result.reason), onRetryCatalog)
                    }
                    is VisaLoad.Ready -> {
                        val countries = result.data.rules
                        item {
                            Text("تاریخ نسخه داده‌ها: " + (result.data.sourceDataModifiedOn ?: "نامشخص"),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        if (search.isBlank()) {
                            item {
                                VisaInfoBox("اطلاعات ویزا همراه برنامه نصب شده و برای جست‌وجو نیازی به اینترنت ندارد. قوانین ممکن است پس از تاریخ این نسخه تغییر کرده باشند.")
                            }
                        } else {
                            val matches = countries.filter {
                                VisaCountries.matches(it.destination, it.upstreamCountryName, search)
                            }.sortedBy { VisaCountries.name(it.destination) }
                            item {
                                Text(
                                    "نتایج جست‌وجو (" + matches.size + ")",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold,
                                )
                            }
                            if (matches.isEmpty()) {
                                item { TravelEmptyState("کشوری با این نام در فهرست منتشرشده وجود ندارد.") }
                            }
                            items(matches, key = { it.destination }) { rule ->
                                Card(
                                    onClick = { onDestination(rule.destination) },
                                    modifier = Modifier.fillMaxWidth().heightIn(min = 58.dp),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                ) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth().padding(15.dp),
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                                    ) {
                                        Text(VisaCountries.flag(rule.destination))
                                        Column(modifier = Modifier.weight(1f)) {
                                            Text(VisaCountries.name(rule.destination), fontWeight = FontWeight.Bold)
                                            Text(
                                                rule.status.persianLabel,
                                                style = MaterialTheme.typography.bodySmall,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            )
                                        }
                                        Text("‹", color = MaterialTheme.colorScheme.primary)
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                val destination = state.selectedDestination
                item {
                    VisaHero(
                        VisaCountries.flag(destination) + "  " + VisaCountries.name(destination),
                        "اطلاعات ورود برای پاسپورت " + VisaCountries.name(state.passport),
                    )
                }
                when (val detail = state.detail) {
                    VisaLoad.Loading, VisaLoad.Idle -> item {
                        TravelLoadingState("در حال بررسی اطلاعات ویزا…")
                    }
                    is VisaLoad.Error -> item {
                        TravelErrorState(visaErrorText(detail.reason), onRetryDetail)
                    }
                    is VisaLoad.Ready -> {
                        val rule = detail.data
                        item { VisaStatusPanel(rule) }
                        item {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(9.dp),
                            ) {
                                VisaFact(
                                    label = "نوع ویزا",
                                    value = rule.status.persianLabel,
                                    modifier = Modifier.weight(1f),
                                )
                                VisaFact(
                                    label = "مدت اقامت",
                                    value = rule.stayDays?.let { it.toString() + " روز" } ?: "ثبت نشده",
                                    modifier = Modifier.weight(1f),
                                )
                                VisaFact(
                                    label = "سطح استناد",
                                    value = visaSourceScope(rule.sourceLevel),
                                    modifier = Modifier.weight(1f),
                                )
                            }
                        }
                        item {
                            VisaDetailCard("شرایط و نکات مهم ورود") {
                                Text(rule.notes ?: "شرایط تکمیلی در داده منتشرشده ثبت نشده است.",
                                    style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                        item {
                            VisaDetailCard("منابع اطلاعات") {
                                Text(
                                    "نوع استناد: " + visaSourceScope(rule.sourceLevel),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                                if (rule.sourceUrl != null) {
                                    OutlinedButton(
                                        onClick = { onSource(rule.sourceUrl) },
                                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                                    ) { Text("مشاهده منبع اطلاعات ↗") }
                                } else {
                                    Text("پیوند منبع برای این قانون منتشر نشده است.")
                                }
                            }
                        }
                        item {
                            VisaDetailCard("تاریخ اطلاعات آفلاین") {
                                Text("آخرین بررسی منبع: " +
                                    (rule.verifiedOn ?: "تاریخ بررسی ثبت نشده"))
                                Text("آخرین به‌روزرسانی فایل مقصد: " +
                                    (rule.destinationUpdatedOn ?: "تاریخ به‌روزرسانی ثبت نشده"),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        item {
                            OutlinedButton(
                                onClick = { onAlert(rule.passport, rule.destination) },
                                modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp),
                                shape = RoundedCornerShape(16.dp),
                            ) {
                                Text("اطلاع از تغییر قوانین (تلگرام)")
                            }
                        }
                        item {
                            Text(
                                "این داده‌ها آفلاین هستند و خودکار به‌روز نمی‌شوند. " +
                                    "منبع داده: TravelRequirements.info — AXG Sp. z o.o. (CC BY 4.0). " +
                                    "این راهنما صرفاً اطلاع‌رسانی است. شرایط ورود به نوع گذرنامه، هدف سفر و وضعیت مسافر بستگی دارد. پیش از سفر اطلاعات را با مرجع مسئول بررسی کنید.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun VisaHero(title: String, subtitle: String) {
    Box(
        modifier = Modifier.fillMaxWidth().height(154.dp)
            .clip(RoundedCornerShape(24.dp))
            .background(
                Brush.linearGradient(
                    listOf(Color(0xFF0B3154), Color(0xFF27618D), Color(0xFF7697B4))
                )
            ),
        contentAlignment = Alignment.CenterStart,
    ) {
        Column(
            modifier = Modifier.padding(22.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            Text(
                title,
                style = MaterialTheme.typography.titleLarge,
                color = Color.White,
                fontWeight = FontWeight.Bold,
            )
            Text(
                subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White.copy(alpha = 0.9f),
            )
        }
    }
}

@Composable
private fun VisaDestinationCard(code: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Card(
        onClick = onClick,
        modifier = modifier.heightIn(min = 112.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f)),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(vertical = 13.dp, horizontal = 6.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(VisaCountries.flag(code), style = MaterialTheme.typography.headlineSmall)
            Text(
                VisaCountries.name(code),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
private fun VisaStatusPanel(rule: VisaRule) {
    val background = when (rule.status) {
        VisaStatus.FREE, VisaStatus.MOVEMENT -> Color(0xFFE2F6EA)
        VisaStatus.BANNED -> Color(0xFFFFE9E9)
        VisaStatus.UNCONFIRMED, VisaStatus.UNKNOWN -> Color(0xFFF4F0E6)
        else -> Color(0xFFE5F0FC)
    }
    Card(
        modifier = Modifier.fillMaxWidth().semantics {
            contentDescription = "وضعیت ویزا: " + rule.status.persianLabel
        },
        colors = CardDefaults.cardColors(containerColor = background),
        shape = RoundedCornerShape(18.dp),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(17.dp),
            verticalArrangement = Arrangement.spacedBy(7.dp),
        ) {
            Text(rule.status.persianLabel, fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.titleLarge, color = Color(0xFF163A50))
            Text("برای دارندگان پاسپورت " + VisaCountries.name(rule.passport),
                style = MaterialTheme.typography.bodyMedium, color = Color(0xFF345569))
            if (rule.status == VisaStatus.UNKNOWN || rule.status == VisaStatus.UNCONFIRMED) {
                Text("عدم تأیید اطلاعات به معنی معافیت از ویزا نیست.",
                    color = Color(0xFF754D19), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun VisaFact(label: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.heightIn(min = 114.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f)),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(9.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(label, textAlign = TextAlign.Center,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, textAlign = TextAlign.Center,
                style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun VisaDetailCard(title: String, content: @Composable () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f)),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(17.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            content()
        }
    }
}

@Composable
private fun VisaInfoBox(message: String) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Text(
            message,
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun VisaPassportDialog(
    selected: String,
    supportedCodes: List<String>,
    onSelect: (String) -> Unit,
    onClose: () -> Unit,
) {
    var query by rememberSaveable { mutableStateOf("") }
    val passportCodes = remember(query) {
        (supportedCodes.ifEmpty { VisaCountries.allPassportCodes() }).filter {
            VisaCountries.matches(it, "", query)
        }
    }
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("کشور صادرکننده پاسپورت") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    label = { Text("جست‌وجوی کشور") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                LazyColumn(modifier = Modifier.heightIn(max = 340.dp)) {
                    items(passportCodes, key = { it }) { code ->
                        TextButton(
                            onClick = { onSelect(code) },
                            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                        ) {
                            Text(
                                VisaCountries.flag(code) + "  " + VisaCountries.name(code) +
                                    if (code == selected) "  ✓" else "",
                                modifier = Modifier.fillMaxWidth(),
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onClose) { Text("بستن") }
        },
    )
}

internal fun visaSourceScope(raw: String?): String = when (raw?.lowercase()) {
    "row", "passport" -> "مختص پاسپورت"
    "shared", "default", "destination", "policy" -> "سیاست کلی مقصد"
    else -> "نامشخص"
}

internal fun visaErrorText(reason: VisaFailure): String = when (reason) {
    VisaFailure.NOT_FOUND -> "اطلاعات این گذرنامه یا مقصد در بسته آفلاین فعلی موجود نیست."
    VisaFailure.INVALID -> "بسته اطلاعات ویزا در این نسخه ناقص یا آسیب‌دیده است."
}
