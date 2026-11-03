package com.abolfazl260.flightiranbot24

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.abolfazl260.flightiranbot24.presentation.components.TravelBottomNavigation
import com.abolfazl260.flightiranbot24.presentation.components.TravelEmptyState
import com.abolfazl260.flightiranbot24.presentation.components.TravelErrorState
import com.abolfazl260.flightiranbot24.presentation.components.TravelLoadingState
import com.abolfazl260.flightiranbot24.presentation.components.TravelTab
import com.abolfazl260.flightiranbot24.presentation.components.TravelToolbar
import java.net.URI

/** Generic Compose presentation of any published airport's existing typed JSON blocks. */
@Composable
internal fun AirportGuideScreen(
    index: AirportContentIndex?,
    page: AirportContentPage?,
    airportNames: Map<String, AirportRow>,
    selectedCode: String?,
    indexLoading: Boolean,
    detailLoading: Boolean,
    indexError: Boolean,
    detailError: Boolean,
    offline: Boolean,
    onSelectAirport: (String) -> Unit,
    onBack: () -> Unit,
    onRetry: () -> Unit,
    onLink: (String) -> Unit,
    onHome: () -> Unit,
    onPrices: () -> Unit,
    onChecklist: () -> Unit,
    onServices: () -> Unit,
) {
    var query by rememberSaveable { mutableStateOf("") }
    var expanded by rememberSaveable(selectedCode) { mutableStateOf<String?>(null) }
    val available = index?.airports.orEmpty()
    val rows = available.map { ref ->
        airportNames[ref.iata] ?: AirportRow(ref.iata, ref.iata, "", "")
    }
    val matches = filterAirports(rows, query).map { it.code }.toSet()
    val visible = available.filter { it.iata in matches }

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
                    title = if (selectedCode == null) "راهنمای فرودگاه‌ها"
                            else airportNames[selectedCode]?.name ?: selectedCode,
                    onBack = onBack,
                )
            }
            if (selectedCode == null) {
                item {
                    Text(
                        "راهنمای مسافر بر اساس اطلاعات تأییدشده هر فرودگاه",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                if (indexLoading) item { TravelLoadingState() }
                if (indexError && index == null) {
                    item { TravelErrorState("فهرست فرودگاه‌ها دریافت نشد.", onRetry) }
                } else if (index != null) {
                    if (offline) item { AirportOfflineNotice() }
                    item {
                        OutlinedTextField(
                            value = query,
                            onValueChange = { query = it },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                            shape = RoundedCornerShape(16.dp),
                            label = { Text("جست‌وجوی نام فرودگاه یا کد IATA") },
                        )
                    }
                    item {
                        Text(
                            available.size.toString() + " فرودگاه دارای اطلاعات منتشرشده",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    if (visible.isEmpty()) {
                        item {
                            TravelEmptyState("برای این جست‌وجو اطلاعات تأییدشده‌ای منتشر نشده است.")
                        }
                    } else {
                        items(visible, key = { it.iata }) { ref ->
                            AirportSelectionCard(
                                name = airportNames[ref.iata]?.name ?: ref.iata,
                                code = ref.iata,
                                onClick = { onSelectAirport(ref.iata) },
                            )
                        }
                    }
                    item {
                        Text(
                            "فرودگاه‌های فاقد داده تأییدشده تا زمان انتشار اطلاعات نمایش داده نمی‌شوند.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            } else {
                item {
                    Text(
                        "راهنمای فرودگاه · " + selectedCode,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                if (detailLoading) item { TravelLoadingState("در حال دریافت اطلاعات فرودگاه…") }
                if (detailError || (page == null && !detailLoading)) {
                    item {
                        TravelErrorState(
                            "اطلاعات این فرودگاه در دسترس نیست؛ دوباره تلاش کنید.",
                            onRetry,
                        )
                    }
                } else if (page != null) {
                    if (offline) item { AirportOfflineNotice() }
                    item {
                        Text(
                            page.sections.size.toString() + " بخش اطلاعات تأییدشده",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    items(page.sections, key = { it.id }) { section ->
                        AirportSectionCard(
                            section = section,
                            isExpanded = expanded == section.id,
                            onToggle = {
                                expanded = if (expanded == section.id) null else section.id
                            },
                            onLink = onLink,
                        )
                    }
                    item {
                        Text(
                            "زمان پرواز، ترمینال، قوانین بار و خدمات ممکن است تغییر کنند. "
                                + "برای روز سفر، اعلام نهایی ایرلاین و فرودگاه ملاک است.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AirportOfflineNotice() {
    Text(
        "نسخه آفلاین نمایش داده می‌شود و ممکن است تازه‌ترین تغییرات را شامل نشود.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.error,
    )
}

@Composable
private fun AirportSelectionCard(name: String, code: String, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(19.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.45f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(18.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(
                    code,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text("‹", style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
private fun AirportSectionCard(
    section: AirportContentSection,
    isExpanded: Boolean,
    onToggle: () -> Unit,
    onLink: (String) -> Unit,
) {
    Card(
        onClick = onToggle,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.45f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        section.title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    section.subtitle?.let {
                        Text(it, style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Text(if (isExpanded) "⌃" else "‹",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (isExpanded) {
                section.blocks.forEach { block ->
                    AirportBlockView(block, onLink)
                }
                if (section.sources.isNotEmpty()) {
                    Text(
                        "منابع اطلاعات",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    section.sources.forEachIndexed { index, source ->
                        TextButton(onClick = { onLink(source) }) {
                            val host = runCatching { URI(source).host }.getOrNull().orEmpty()
                            Text("منبع " + (index + 1) + " · " + host)
                        }
                    }
                }
                Text(
                    "آخرین بررسی: " + section.reviewedAt.take(10),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun AirportBlockView(block: AirportContentBlock, onLink: (String) -> Unit) {
    when (block) {
        is AirportContentBlock.Text -> {
            Text(block.content, style = MaterialTheme.typography.bodyMedium)
        }
        is AirportContentBlock.Bullets -> {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                block.items.forEach { item ->
                    Text("•  " + item, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
        is AirportContentBlock.Link -> {
            TextButton(onClick = { onLink(block.url) }) { Text(block.title) }
        }
        is AirportContentBlock.Image -> {
            Text(block.alt, style = MaterialTheme.typography.bodyMedium)
            block.caption?.let {
                Text(it, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            TextButton(onClick = { onLink(block.url) }) { Text("مشاهده تصویر") }
        }
        is AirportContentBlock.Video -> {
            Text(block.title, style = MaterialTheme.typography.bodyMedium)
            block.credit?.let {
                Text(it, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            TextButton(onClick = { onLink(block.url) }) { Text("مشاهده ویدیو") }
        }
        is AirportContentBlock.Map -> {
            Text(block.title, style = MaterialTheme.typography.bodyMedium)
            TextButton(onClick = { onLink(block.externalUrl) }) {
                Text("مشاهده موقعیت روی نقشه")
            }
        }
        is AirportContentBlock.FlightBoard -> {
            Text(
                "برای مشاهده وضعیت پرواز، اطلاعات روز را در مرجع رسمی بررسی کنید.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        is AirportContentBlock.Experience -> {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(block.text, style = MaterialTheme.typography.bodyMedium)
                Text(
                    "امتیاز " + block.rating + " از ۵ · تاریخ مراجعه " + block.visitDate,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
