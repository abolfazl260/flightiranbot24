package com.abolfazl260.flightiranbot24

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme

/** Offline, Persian-only and native privacy notice; its content never opens a website. */
class PrivacyPolicyActivity : ComponentActivity() {
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(PersianContext.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TravelTheme {
                PrivacyPolicyScreen(
                    onBack = ::finish,
                    onOpenChecklist = {
                        startActivity(Intent(this, ChecklistActivity::class.java))
                    },
                    onOpenAppSettings = {
                        try {
                            startActivity(
                                Intent(
                                    Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                    Uri.fromParts("package", packageName, null),
                                ),
                            )
                        } catch (_: ActivityNotFoundException) {
                            Toast.makeText(this, R.string.link_unavailable, Toast.LENGTH_LONG).show()
                        }
                    },
                    onSupport = {
                        try {
                            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(BotLinks.SUPPORT)))
                        } catch (_: ActivityNotFoundException) {
                            Toast.makeText(this, R.string.link_unavailable, Toast.LENGTH_LONG).show()
                        }
                    },
                )
            }
        }
    }
}

private data class PrivacySection(
    val title: String,
    val subtitle: String,
    val body: String,
)

@Composable
internal fun PrivacyPolicyScreen(
    onBack: () -> Unit,
    onOpenChecklist: () -> Unit = {},
    onOpenAppSettings: () -> Unit = {},
    onSupport: () -> Unit = {},
) {
    var expandedSection by rememberSaveable { mutableIntStateOf(-1) }
    val sections = listOf(
        PrivacySection(
            stringResource(R.string.privacy_local_title),
            stringResource(R.string.privacy_local_subtitle),
            stringResource(R.string.privacy_local_body),
        ),
        PrivacySection(
            stringResource(R.string.privacy_network_title),
            stringResource(R.string.privacy_network_subtitle),
            stringResource(R.string.privacy_network_body),
        ),
        PrivacySection(
            stringResource(R.string.privacy_permissions_title),
            stringResource(R.string.privacy_permissions_subtitle),
            stringResource(R.string.privacy_permissions_body),
        ),
        PrivacySection(
            stringResource(R.string.privacy_telegram_title),
            stringResource(R.string.privacy_telegram_subtitle),
            stringResource(R.string.privacy_telegram_body),
        ),
        PrivacySection(
            stringResource(R.string.privacy_security_title),
            stringResource(R.string.privacy_security_subtitle),
            stringResource(R.string.privacy_security_body),
        ),
        PrivacySection(
            stringResource(R.string.privacy_deletion_title),
            stringResource(R.string.privacy_deletion_subtitle),
            stringResource(R.string.privacy_deletion_body),
        ),
        PrivacySection(
            stringResource(R.string.privacy_changes_title),
            stringResource(R.string.privacy_changes_subtitle),
            stringResource(R.string.privacy_changes_body),
        ),
    )

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            Surface(shadowElevation = 2.dp, color = MaterialTheme.colorScheme.surface) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .windowInsetsPadding(WindowInsets.statusBars)
                        .heightIn(min = 56.dp)
                        .padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = stringResource(R.string.open_privacy),
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                    )
                    TextButton(
                        onClick = onBack,
                        modifier = Modifier.heightIn(min = 48.dp),
                    ) {
                        Text(stringResource(R.string.privacy_back))
                    }
                }
            }
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            PrivacyOverviewCard()
            Text(
                text = stringResource(R.string.privacy_sections_heading),
                modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            sections.forEachIndexed { index, section ->
                PrivacyExpandableCard(
                    index = index,
                    section = section,
                    expanded = expandedSection == index,
                    onToggle = {
                        expandedSection = if (expandedSection == index) -1 else index
                    },
                )
            }

            PrivacyDataActions(
                onOpenChecklist = onOpenChecklist,
                onOpenAppSettings = onOpenAppSettings,
            )
            PrivacySupportCard(onSupport)
            Text(
                text = stringResource(R.string.privacy_last_updated),
                modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Start,
            )
            Text(
                text = stringResource(R.string.privacy_disclaimer),
                modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Start,
            )
        }
    }
}

@Composable
private fun PrivacyOverviewCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(RoundedCornerShape(15.dp))
                        .background(MaterialTheme.colorScheme.primaryContainer),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "✓",
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold,
                        fontSize = 25.sp,
                    )
                }
                Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(
                        stringResource(R.string.privacy_overview_title),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        stringResource(R.string.privacy_intro),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        lineHeight = 21.sp,
                    )
                }
            }
            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.7f))
            Text(
                stringResource(R.string.privacy_summary_heading),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
            )
            PrivacySummaryRow(stringResource(R.string.privacy_summary_local))
            PrivacySummaryRow(stringResource(R.string.privacy_summary_network))
            PrivacySummaryRow(stringResource(R.string.privacy_summary_permissions))
        }
    }
}

@Composable
private fun PrivacySummaryRow(text: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box(
            modifier = Modifier.size(22.dp).background(
                MaterialTheme.colorScheme.primaryContainer, CircleShape,
            ),
            contentAlignment = Alignment.Center,
        ) {
            Text("✓", color = MaterialTheme.colorScheme.primary, fontSize = 13.sp)
        }
        Text(text, style = MaterialTheme.typography.bodyMedium, lineHeight = 23.sp)
    }
}

@Composable
private fun PrivacyExpandableCard(
    index: Int,
    section: PrivacySection,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    val state = if (expanded) {
        stringResource(R.string.privacy_expanded)
    } else {
        stringResource(R.string.privacy_collapsed)
    }
    Card(
        onClick = onToggle,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 76.dp)
            .testTag("privacy-section-$index")
            .semantics { stateDescription = state },
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.9f)),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Box(
                    modifier = Modifier
                        .size(38.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(MaterialTheme.colorScheme.primaryContainer),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = listOf("۱", "۲", "۳", "۴", "۵", "۶", "۷")[index],
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold,
                    )
                }
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                ) {
                    Text(
                        section.title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        section.subtitle,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        lineHeight = 20.sp,
                    )
                }
                Text(
                    text = if (expanded) "⌃" else "⌄",
                    fontSize = 23.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (expanded) {
                HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.65f))
                Text(
                    section.body,
                    style = MaterialTheme.typography.bodyMedium,
                    lineHeight = 25.sp,
                    textAlign = TextAlign.Start,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun PrivacyDataActions(
    onOpenChecklist: () -> Unit,
    onOpenAppSettings: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                stringResource(R.string.privacy_data_heading),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                stringResource(R.string.privacy_data_hint),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                lineHeight = 22.sp,
            )
            OutlinedButton(
                onClick = onOpenChecklist,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
            ) {
                Text(stringResource(R.string.privacy_open_checklist))
            }
            OutlinedButton(
                onClick = onOpenAppSettings,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
            ) {
                Text(stringResource(R.string.privacy_open_app_settings))
            }
        }
    }
}

@Composable
private fun PrivacySupportCard(onSupport: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surfaceVariant,
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                stringResource(R.string.privacy_help_heading),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center,
            )
            Button(
                onClick = onSupport,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
            ) {
                Text(stringResource(R.string.privacy_contact_support))
            }
        }
    }
}
