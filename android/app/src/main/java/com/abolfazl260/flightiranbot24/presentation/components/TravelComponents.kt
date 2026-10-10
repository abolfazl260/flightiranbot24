package com.abolfazl260.flightiranbot24.presentation.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTokens

/** Shared Compose building blocks. Labels are always supplied in Persian. */
@Composable
internal fun TravelSectionHeading(title: String, description: String) {
    Column(verticalArrangement = Arrangement.spacedBy(TravelTokens.spacingSm)) {
        Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text(
            description,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
internal fun TravelServiceCard(
    title: String,
    subtitle: String,
    symbol: String,
    onClick: () -> Unit,
) {
    var hasFocus by remember { mutableStateOf(false) }
    Card(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = TravelTokens.touchTarget)
            .onFocusChanged { hasFocus = it.isFocused },
        border = if (hasFocus) BorderStroke(2.dp, MaterialTheme.colorScheme.primary)
                 else BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(TravelTokens.spacingLg),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(TravelTokens.spacingLg),
        ) {
            Text(
                symbol,
                modifier = Modifier.clearAndSetSemantics { },
                style = MaterialTheme.typography.headlineSmall,
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleMedium)
                Text(
                    subtitle,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            Text("‹", modifier = Modifier.clearAndSetSemantics { },
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
internal fun RowScope.TravelNavigationItem(
    label: String,
    symbol: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    NavigationBarItem(
        selected = selected,
        onClick = onClick,
        icon = { Text(symbol, modifier = Modifier.clearAndSetSemantics { }) },
        label = { Text(label) },
        alwaysShowLabel = true,
    )
}

@Composable
internal fun TravelToolbar(title: String, onBack: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            title,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.weight(1f),
        )
        TextButton(onClick = onBack, modifier = Modifier.heightIn(min = TravelTokens.touchTarget)) {
            Text("بازگشت")
        }
    }
}

@Composable
internal fun TravelFormField(value: String, label: String, onValueChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        singleLine = true,
        textStyle = MaterialTheme.typography.bodyLarge,
        modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
    )
}

@Composable
internal fun TravelLoadingState(message: String = "در حال بارگذاری…") {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = TravelTokens.spacingLg),
        horizontalArrangement = Arrangement.spacedBy(TravelTokens.spacingMd),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        CircularProgressIndicator(
            modifier = Modifier.semantics { contentDescription = message },
        )
        Text(message, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
internal fun TravelEmptyState(message: String) {
    Text(
        message,
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        textAlign = TextAlign.Start,
        modifier = Modifier.fillMaxWidth().padding(vertical = TravelTokens.spacingLg),
    )
}

@Composable
internal fun TravelErrorState(message: String, onRetry: (() -> Unit)? = null) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = TravelTokens.spacingLg),
        verticalArrangement = Arrangement.spacedBy(TravelTokens.spacingSm),
    ) {
        Text(message, color = MaterialTheme.colorScheme.error,
            style = MaterialTheme.typography.bodyMedium)
        if (onRetry != null) {
            TextButton(
                onClick = onRetry,
                modifier = Modifier.heightIn(min = TravelTokens.touchTarget),
            ) { Text("تلاش مجدد") }
        }
    }
}

@Composable
internal fun TravelListRow(
    title: String,
    subtitle: String,
    details: String?,
    expanded: Boolean,
    onClick: () -> Unit,
) {
    var hasFocus by remember { mutableStateOf(false) }
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth()
            .heightIn(min = TravelTokens.touchTarget)
            .onFocusChanged { hasFocus = it.isFocused }
            .semantics { stateDescription = if (expanded) "جزئیات باز است" else "جزئیات بسته است" },
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(if (hasFocus) 2.dp else 1.dp,
            if (hasFocus) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(TravelTokens.spacingLg),
            verticalArrangement = Arrangement.spacedBy(TravelTokens.spacingXs),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(subtitle, style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary)
            if (expanded && !details.isNullOrBlank()) {
                Text(details, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
internal fun TravelConfirmDialog(
    title: String,
    message: String,
    confirmText: String,
    dismissText: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = { Text(message) },
        confirmButton = {
            TextButton(onClick = onConfirm, modifier = Modifier.heightIn(min = TravelTokens.touchTarget)) {
                Text(confirmText)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, modifier = Modifier.heightIn(min = TravelTokens.touchTarget)) {
                Text(dismissText)
            }
        },
    )
}

@Composable
private fun TravelComponentGallery() {
    TravelTheme {
        Column(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            TravelSectionHeading("امکانات سفر", "راهنمای آفلاین سفر با نمایش فارسی")
            TravelServiceCard("فهرست فرودگاه‌ها", "قابل استفاده در اپ", "✈", {})
            TravelServiceCard("راهنمای ویزا", "ورود به تلگرام", "▣", {})
            TravelToolbar("فرودگاه‌ها", {})
            TravelFormField("", "نام فرودگاه یا کد IATA", {})
            TravelEmptyState("فرودگاهی با این مشخصات پیدا نشد.")
            TravelErrorState("فهرست فرودگاه‌ها در دسترس نیست.") {}
        }
    }
}

@Preview(name = "موبایل کوچک - RTL", widthDp = 320, heightDp = 720, showBackground = true)
@Composable
private fun PreviewSmall() = TravelComponentGallery()

@Preview(name = "موبایل بزرگ - RTL", widthDp = 420, heightDp = 900, showBackground = true)
@Composable
private fun PreviewLarge() = TravelComponentGallery()
