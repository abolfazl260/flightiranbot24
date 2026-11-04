package com.abolfazl260.flightiranbot24

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.abolfazl260.flightiranbot24.presentation.components.TravelBottomNavigation
import com.abolfazl260.flightiranbot24.presentation.components.TravelEmptyState
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelTab
import com.abolfazl260.flightiranbot24.presentation.components.TravelToolbar

@Composable
internal fun AirlineGuideScreen(
    index: List<AirlineReference>?, page: AirlinePage?, selected: String?, sectionId: String?,
    loading: Boolean, error: Boolean, offline: Boolean,
    onSelect: (String) -> Unit, onSection: (String) -> Unit, onBack: () -> Unit,
    onRetry: () -> Unit, onLink: (String) -> Unit, onAirport: (String) -> Unit,
    onShare: (AirlineReference) -> Unit, onHome: () -> Unit, onServices: () -> Unit,
    onPrices: () -> Unit, onChecklist: () -> Unit,
) {
    var query by rememberSaveable { mutableStateOf("") }
    var region by rememberSaveable { mutableStateOf("all") }
    val ref = index?.firstOrNull { it.id == selected }
    val section = page?.sections?.firstOrNull { it.id == sectionId }
    val holder = rememberSaveableStateHolder()
    Scaffold(bottomBar = {
        TravelBottomNavigation(TravelTab.SERVICES, onHome, onPrices, onChecklist, onServices)
    }) { padding ->
        // Keep saved list state untouched until real content is ready. Rendering
        // a one-row loading list here would clamp restored scroll positions.
        if (loading || error) {
            Column(Modifier.fillMaxSize().padding(padding).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)) {
                TravelToolbar(ref?.name ?: "ایرلاین‌ها", onBack)
                if (loading) TravelLoadingState()
                else TravelErrorState("راهنمای ایرلاین دریافت نشد.", onRetry)
            }
        } else {
            holder.SaveableStateProvider((selected ?: "directory") + "/" + (sectionId ?: "overview")) {
                val scroll = rememberLazyListState()
                LazyColumn(
                    state = scroll, modifier = Modifier.fillMaxSize().padding(padding),
                    contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item { TravelToolbar(section?.title ?: ref?.name ?: "ایرلاین‌ها", onBack) }
                    when {
                        selected == null -> {
                            if (offline) item { OfflineAirlineNotice() }
                            item {
                                OutlinedTextField(query, { query = it }, Modifier.fillMaxWidth(),
                                    label = { Text("جست‌وجوی نام، نام پیشین یا کد ایرلاین") }, singleLine = true)
                            }
                            item {
                                Row(Modifier.horizontalScroll(rememberScrollState()),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    listOf("all" to "همه", "iran" to "ایرانی", "foreign" to "خارجی").forEach { (key, title) ->
                                        FilterChip(region == key, { region = key }, label = { Text(title) })
                                    }
                                }
                            }
                            val visible = filterAirlines(index.orEmpty(), query, region)
                            if (visible.isEmpty()) item { TravelEmptyState("ایرلاینی برای نمایش پیدا نشد.") }
                            items(visible, key = { it.id }) { airline ->
                                Card(onClick = { onSelect(airline.id) }, modifier = Modifier.fillMaxWidth().heightIn(min = 72.dp)) {
                                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                        Text(airline.name, fontWeight = FontWeight.Bold)
                                        Text(airline.nameEn + " · " + airline.codes.joinToString(" / "))
                                        Text(airline.countryName)
                                        Text("راهنما در حال تکمیل", style = MaterialTheme.typography.labelMedium)
                                        Text("آخرین بررسی هویت: " + airline.reviewedAt.take(10), style = MaterialTheme.typography.labelSmall)
                                    }
                                }
                            }
                        }
                        ref == null || page == null -> item {
                            TravelEmptyState("این راهنما هنوز منتشر نشده یا فعلاً در دسترس نیست.")
                        }
                        sectionId != null -> {
                            if (offline) item { OfflineAirlineNotice() }
                            if (section == null) item { TravelEmptyState("این بخش هنوز منتشر نشده یا نیازمند بررسی دوباره است.") }
                            else {
                                item { Text("آخرین بررسی: " + section.reviewedAt.take(10)) }
                                section.scope?.let { scope -> item {
                                    Text(scope.note)
                                    Text("سهمیه و شرایط دقیق از روی بلیت و شرکت اجراکننده تعیین می‌شود.")
                                    scope.route?.let { Text("مسیر: " + it) }
                                    scope.fare?.let { Text("نوع نرخ: " + it) }
                                    scope.cabin?.let { Text("کلاس کابین: " + it) }
                                    scope.operatingCarrier?.let { id ->
                                        val carrier = index?.firstOrNull { it.id == id }
                                        Text("شرکت اجراکننده: " + (carrier?.name ?: "نیازمند تأیید"))
                                    }
                                    val seller = mapOf("airline" to "خرید مستقیم از ایرلاین",
                                        "agency" to "خرید از آژانس", "third_party" to "خرید از واسطه",
                                        "unknown" to "طبق فروشنده درج‌شده در بلیت")
                                    Text("دامنه فروش: " + (seller[scope.seller] ?: "نیازمند تأیید"))
                                    when (scope.journeyType) {
                                        "domestic" -> Text("مخصوص پرواز داخلی")
                                        "international" -> Text("مخصوص پرواز خارجی")
                                    }
                                } }
                                items(section.blocks) { block -> AirlineBlockView(block, onLink, onAirport) }
                                item { AirlineHeading("منابع و آخرین قوانین") }
                                items(section.sources) { source ->
                                    TextButton(onClick = { onLink(source) }) { Text("بررسی مرجع · " + java.net.URI(source).host) }
                                }
                            }
                        }
                        else -> {
                            if (offline) item { OfflineAirlineNotice() }
                            item {
                                Text(ref.nameEn + " · " + ref.countryName + " · " + ref.codes.joinToString(" / "))
                                Text("آخرین بررسی راهنما: " + page.reviewedAt.take(10))
                                Text("راهنما در حال تکمیل؛ فقط بخش‌های بررسی‌شده نمایش داده می‌شوند.")
                            }
                            item {
                                TextButton(onClick = { onLink(ref.website) }) { Text("وب‌سایت رسمی ایرلاین") }
                                TextButton(onClick = { onShare(ref) }) { Text("اشتراک‌گذاری") }
                            }
                            if (page.sections.isEmpty()) item {
                                TravelEmptyState("بخش منتشرشده و معتبر برای این راهنما در دسترس نیست.")
                            }
                            items(page.sections, key = { it.id }) { item ->
                                Card(onClick = { onSection(item.id) }, modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp)) {
                                    Column(Modifier.padding(16.dp)) {
                                        Text(item.title, fontWeight = FontWeight.Bold)
                                        Text("آخرین بررسی: " + item.reviewedAt.take(10), style = MaterialTheme.typography.labelSmall)
                                    }
                                }
                            }
                            item { AirlineHeading("تجربه‌های مسافران و امتیازها") }
                            item {
                                Text("تجربهٔ شخصی کاربر، نه مقررات رسمی شرکت هواپیمایی یا ارزیابی ایمنی.")
                                Text("تجربهٔ دارای مجوز انتشار برای این ایرلاین هنوز متصل نشده است.")
                                Text("تعداد رأی معتبر: " + page.ratingCount)
                                Text("میانگین و مقایسه تا تعیین حداقل نمونهٔ معتبر نمایش داده نمی‌شود.")
                                if (page.ratingCount > 0) page.criterionCounts.forEach { (key, count) ->
                                    Text(AirlineContentParser.criteria.getValue(key) + ": " + count + " رأی")
                                }
                                TextButton(onClick = { onLink(BotLinks.SUPPORT) }) { Text("گزارش یا درخواست اصلاح محتوا") }
                            }
                        }
                    }
                    item { TextButton(onClick = onRetry) { Text("بررسی دوباره اطلاعات") } }
                }
            }
        }
    }
}

@Composable
private fun AirlineHeading(title: String) = Text(title, Modifier.semantics { heading() },
    style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)

@Composable
private fun OfflineAirlineNotice() = Text(
    "دریافت دادهٔ تازه ممکن نشد؛ نسخهٔ همراه برنامه با تاریخ بررسی درج‌شده نمایش داده می‌شود. " +
        "پیش از سفر آخرین قوانین را در سایت ایرلاین تأیید کنید.",
    style = MaterialTheme.typography.bodySmall,
)

@Composable
private fun AirlineBlockView(block: AirlineBlock, onLink: (String) -> Unit, onAirport: (String) -> Unit) {
    when (block) {
        is AirlineBlock.Content -> when (val content = block.block) {
            is AirportContentBlock.Text -> Text(content.content)
            is AirportContentBlock.Bullets -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                content.items.forEach { Text("• " + it) }
            }
            is AirportContentBlock.Link -> TextButton(onClick = { onLink(content.url) }) { Text(content.title) }
            else -> Unit
        }
        is AirlineBlock.Airport -> TextButton(onClick = { onAirport(block.iata) }) { Text(block.title + " · " + block.iata) }
        is AirlineBlock.Media -> Column {
            Text(block.title)
            Text(block.attribution)
            TextButton(onClick = { onLink(block.url) }) { Text("مشاهده رسانه در منبع") }
        }
        is AirlineBlock.Fleet -> Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                AirlineHeading(block.manufacturer + " " + block.model)
                Text("تعداد: " + (block.count?.toString() ?: "تأیید نشده"))
                Text("تاریخ مشاهده: " + block.observedAt.take(10))
                val relationship = mapOf("owned" to "ملکی", "operated" to "بهره‌برداری", "leased" to "اجاره‌ای", "unknown" to "نامعلوم")
                val status = mapOf("active" to "فعال", "stored" to "پارک‌شده", "leased-in" to "اجاره ورودی", "leased-out" to "اجاره خروجی", "retired" to "بازنشسته", "unknown" to "تأیید نشده")
                Text("نوع رابطه: " + relationship[block.relationship] + " · وضعیت: " + status[block.status])
                block.configuration?.let { Text(it) }
                Text("نوع هواپیما و چیدمان روز سفر باید جداگانه تأیید شود.")
                block.sources.forEach { source ->
                    TextButton(onClick = { onLink(source) }) { Text("مرجع ناوگان") }
                }
            }
        }
    }
}
