package com.abolfazl260.flightiranbot24

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
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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
    var region by rememberSaveable { mutableStateOf("all") }
    var alphabeticOrder by rememberSaveable { mutableStateOf(false) }
    var expanded by rememberSaveable(selectedCode) { mutableStateOf<String?>(null) }
    val available = index?.airports.orEmpty()
    val rows = available.map { ref ->
        airportNames[ref.iata] ?: AirportRow(ref.iata, ref.iata, "", "")
    }
    val matches = filterAirports(rows, query).map { it.code }.toSet()
    val filtered = available.filter { ref ->
        ref.iata in matches && when (region) {
            "iran" -> airportNames[ref.iata]?.country == "IR"
            "foreign" -> airportNames[ref.iata]?.country != "IR"
            else -> true
        }
    }
    val alphabetical = filtered.sortedBy { airportNames[it.iata]?.name ?: it.iata }
    val featuredCodes = listOf("MHD", "KIH", "THR")
    val visible = if (alphabeticOrder) alphabetical else {
        featuredCodes.mapNotNull { code -> alphabetical.firstOrNull { it.iata == code } } +
            alphabetical.filterNot { it.iata in featuredCodes }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            // Retain the existing shared bottom bar without styling or behavior changes.
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
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item {
                if (selectedCode == null) {
                    AirportDirectoryHeader(onBack)
                } else {
                    TravelToolbar(
                        title = airportNames[selectedCode]?.name ?: selectedCode,
                        onBack = onBack,
                    )
                }
            }
            if (selectedCode == null) {
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
                            shape = RoundedCornerShape(22.dp),
                            placeholder = { Text("جست‌وجوی نام فرودگاه یا کد IATA ...") },
                            trailingIcon = {
                                Text(
                                    "⌕",
                                    style = MaterialTheme.typography.headlineSmall,
                                    color = MaterialTheme.colorScheme.secondary,
                                )
                            },
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = MaterialTheme.colorScheme.surface,
                                unfocusedContainerColor = MaterialTheme.colorScheme.surface,
                            ),
                        )
                    }
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            AirportRegionChip(
                                text = "✈  همه",
                                selected = region == "all",
                                onClick = { region = "all" },
                                modifier = Modifier.weight(1f),
                            )
                            AirportRegionChip(
                                text = "🇮🇷  ایران",
                                selected = region == "iran",
                                onClick = { region = "iran" },
                                modifier = Modifier.weight(1f),
                            )
                            AirportRegionChip(
                                text = "🌐  خارجی",
                                selected = region == "foreign",
                                onClick = { region = "foreign" },
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                    if (query.isBlank() && region == "all" &&
                        featuredCodes.any { code -> available.any { it.iata == code } }
                    ) {
                        item {
                            Text(
                                "✦  فرودگاه‌های پرطرفدار",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(top = 12.dp, bottom = 2.dp),
                            )
                        }
                        item {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                listOf(
                                    Triple("MHD", "مشهد", "MHD"),
                                    Triple("KIH", "کیش", "KIH"),
                                    Triple("THR", "تهران", "THR"),
                                ).filter { (code, _, _) -> available.any { it.iata == code } }
                                    .forEach { (code, name, _) ->
                                        AirportFeaturedCard(
                                            name = name,
                                            code = code,
                                            modifier = Modifier.weight(1f),
                                            onClick = { onSelectAirport(code) },
                                        )
                                    }
                            }
                        }
                    }
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(
                                visible.size.toString() + " فرودگاه با راهنمای منتشرشده",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Surface(
                                onClick = { alphabeticOrder = !alphabeticOrder },
                                shape = RoundedCornerShape(16.dp),
                                color = MaterialTheme.colorScheme.surface,
                                border = BorderStroke(
                                    1.dp,
                                    MaterialTheme.colorScheme.outline,
                                ),
                            ) {
                                Text(
                                    if (alphabeticOrder) "↑  الفبایی" else "↕  مرتب‌سازی",
                                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = FontWeight.SemiBold,
                                )
                            }
                        }
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
                            "با انتشار راهنمای فرودگاه‌های دیگر، آن‌ها نیز به فهرست اضافه می‌شوند.",
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
                            page.sections.size.toString() + " موضوع راهنمای سفر",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    item { ExperiencesPanel("airport:"+page.iata) }
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
        "نسخه ذخیره‌شده روی گوشی نمایش داده می‌شود و ممکن است تازه‌ترین تغییرات را شامل نشود.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.error,
    )
}

@Composable
private fun AirportDirectoryHeader(onBack: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                modifier = Modifier.size(42.dp)
                    .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(13.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text("✈", color = MaterialTheme.colorScheme.onPrimary, fontSize = 24.sp)
            }
            Text(
                "راهنمای فرودگاه‌ها",
                modifier = Modifier.weight(1f),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            TextButton(onClick = onBack, modifier = Modifier.heightIn(min = 48.dp)) {
                Text("بازگشت")
            }
        }
        Text(
            "اطلاعات کاربردی فرودگاه برای برنامه‌ریزی سفر",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun AirportRegionChip(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        onClick = onClick,
        modifier = modifier.height(50.dp),
        shape = RoundedCornerShape(19.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (selected) MaterialTheme.colorScheme.secondary
                else MaterialTheme.colorScheme.surface,
        ),
        border = if (selected) null else BorderStroke(
            1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.6f),
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(
                text,
                style = MaterialTheme.typography.labelMedium,
                color = if (selected) MaterialTheme.colorScheme.onSecondary
                    else MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun AirportFeaturedCard(
    name: String,
    code: String,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Card(
        onClick = onClick,
        modifier = modifier.clip(RoundedCornerShape(21.dp)),
        shape = RoundedCornerShape(21.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.55f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            AirportCityImage(
                code = code,
                modifier = Modifier.fillMaxWidth().height(78.dp),
            )
            Text(
                name,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
            )
            Surface(
                color = MaterialTheme.colorScheme.surfaceVariant,
                shape = RoundedCornerShape(12.dp),
            ) {
                Text(
                    code,
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 3.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.labelMedium,
                )
            }
        }
    }
}

/** City WebPs are already bundled for the ticket-price cards; never create duplicates. */
private fun airportCityDrawable(code: String): Int? = when (code) {
    "AWZ" -> R.drawable.price_city_ahvaz
    "BKK" -> R.drawable.price_city_bangkok
    "BND" -> R.drawable.price_city_bandarabbas
    "DOH" -> R.drawable.price_city_doha
    "DXB" -> R.drawable.price_city_dubai
    "GSM" -> R.drawable.price_city_qeshm
    "IFN" -> R.drawable.price_city_isfahan
    "IKA", "THR" -> R.drawable.price_city_tehran
    "IST" -> R.drawable.price_city_istanbul
    "KER" -> R.drawable.price_city_kerman
    "KIH" -> R.drawable.price_city_kish
    "MHD" -> R.drawable.price_city_mashhad
    "OMH" -> R.drawable.price_city_urmia
    "PEK" -> R.drawable.price_city_beijing
    "SYZ" -> R.drawable.price_city_shiraz
    "TBZ" -> R.drawable.price_city_tabriz
    "ZAH" -> R.drawable.price_city_zahedan
    else -> null
}

/** Fit (never crop) plus an explicit clipped viewport prevents illustration overflow. */
@Composable
private fun AirportCityImage(code: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier.clip(RoundedCornerShape(14.dp)),
        contentAlignment = Alignment.Center,
    ) {
        val illustration = airportCityDrawable(code)
        if (illustration != null) {
            Image(
                painter = painterResource(illustration),
                contentDescription = null,
                modifier = Modifier.fillMaxSize().padding(2.dp),
                contentScale = ContentScale.Fit,
            )
        } else {
            Box(
                modifier = Modifier.fillMaxSize()
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "✈",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

@Composable
private fun AirportSelectionCard(name: String, code: String, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(19.dp)),
        shape = RoundedCornerShape(19.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.55f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().heightIn(min = 94.dp)
                .padding(horizontal = 12.dp, vertical = 9.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            AirportCityImage(
                code = code,
                modifier = Modifier.size(76.dp),
            )
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(
                    name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Surface(
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    shape = RoundedCornerShape(10.dp),
                ) {
                    Text(
                        code,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 9.dp, vertical = 2.dp),
                    )
                }
            }
            Text(
                "‹",
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.primary,
            )
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
            modifier = Modifier.fillMaxWidth().padding(horizontal = 15.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        section.title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    if (!isExpanded) {
                        section.subtitle?.let {
                            Text(
                                it,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
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
            Text("تجربه‌های دارای مجوز انتشار در بخش مشترک تجربه‌ها قابل مشاهده‌اند.")
        }
    }
}
