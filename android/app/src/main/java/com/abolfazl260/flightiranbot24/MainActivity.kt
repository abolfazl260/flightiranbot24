package com.abolfazl260.flightiranbot24

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/**
 * First incremental Kotlin/Compose screen (AND-001). Offline airport and
 * checklist screens remain native Java Activities until their own tasks.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    TravelHomeScreen(onSelect = ::navigateTo)
                }
            }
        }
    }

    private fun navigateTo(destination: HomeDestination) {
        when (destination) {
            HomeDestination.OFFLINE_AIRPORTS ->
                startActivity(Intent(this, AirportDirectoryActivity::class.java))
            HomeDestination.OFFLINE_CHECKLIST ->
                startActivity(Intent(this, ChecklistActivity::class.java))
            HomeDestination.TELEGRAM_BOT,
            HomeDestination.TELEGRAM_AIRPORTS,
            HomeDestination.TELEGRAM_USEFUL -> openUrl(BotLinks.BOT)
            HomeDestination.TELEGRAM_VISA -> openBotCommand("/visa")
            HomeDestination.SUPPORT -> openUrl(BotLinks.SUPPORT)
            HomeDestination.PRIVACY -> openUrl(BotLinks.PRIVACY)
        }
    }

    private fun openBotCommand(command: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
        clipboard?.setPrimaryClip(ClipData.newPlainText("Telegram command", command))
        if (clipboard != null) {
            Toast.makeText(this, R.string.command_copied, Toast.LENGTH_SHORT).show()
        }
        openUrl(BotLinks.BOT)
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
internal fun TravelHomeScreen(onSelect: (HomeDestination) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(WindowInsets.safeDrawing)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = stringResource(R.string.welcome_title),
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
        )
        Text(
            text = stringResource(R.string.welcome_description),
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
        )
        ShortcutSection(
            title = stringResource(R.string.home_offline_heading),
            shortcuts = offlineHomeShortcuts,
            onSelect = onSelect,
        )
        ShortcutSection(
            title = stringResource(R.string.home_online_heading),
            shortcuts = onlineHomeShortcuts,
            onSelect = onSelect,
        )
        Text(
            text = stringResource(R.string.command_hint),
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
        )
        Text(
            text = stringResource(R.string.notice),
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
private fun ShortcutSection(
    title: String,
    shortcuts: List<HomeShortcut>,
    onSelect: (HomeDestination) -> Unit,
) {
    Text(
        text = title,
        style = MaterialTheme.typography.titleMedium,
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
    )
    shortcuts.forEach { shortcut ->
        Button(
            onClick = { onSelect(shortcut.destination) },
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        ) {
            Text(
                text = stringResource(shortcut.labelRes),
                textAlign = TextAlign.Center,
            )
        }
    }
}
