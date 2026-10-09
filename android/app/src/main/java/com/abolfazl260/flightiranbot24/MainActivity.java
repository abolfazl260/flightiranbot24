package com.abolfazl260.flightiranbot24;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.widget.Toast;

/**
 * Native launcher for the existing Telegram travel services.
 * The backend currently authenticates the Web App via Telegram initData,
 * so this app intentionally does not load those protected URLs in a WebView.
 */
public final class MainActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        UiInsets.apply(this, findViewById(R.id.root));

        findViewById(R.id.offlineAirports).setOnClickListener(
                view -> startActivity(new Intent(this, AirportDirectoryActivity.class)));
        findViewById(R.id.checklist).setOnClickListener(
                view -> startActivity(new Intent(this, ChecklistActivity.class)));

        findViewById(R.id.openBot).setOnClickListener(view -> openUrl(BotLinks.BOT));
        findViewById(R.id.openVisa).setOnClickListener(view -> openBotCommand("/visa"));
        findViewById(R.id.openCurrency).setOnClickListener(view -> openBotCommand("/price"));
        findViewById(R.id.openAirports).setOnClickListener(view -> openUrl(BotLinks.BOT));
        findViewById(R.id.openUseful).setOnClickListener(view -> openUrl(BotLinks.BOT));
        findViewById(R.id.openSupport).setOnClickListener(view -> openUrl(BotLinks.SUPPORT));
        findViewById(R.id.openPrivacy).setOnClickListener(view -> openUrl(BotLinks.PRIVACY));
    }

    private void openBotCommand(String command) {
        ClipboardManager clipboard =
                (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (clipboard != null) {
            clipboard.setPrimaryClip(ClipData.newPlainText("Telegram command", command));
            Toast.makeText(this, R.string.command_copied, Toast.LENGTH_SHORT).show();
        }
        openUrl(BotLinks.BOT);
    }

    private void openUrl(String url) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (ActivityNotFoundException exception) {
            Toast.makeText(this, R.string.link_unavailable, Toast.LENGTH_LONG).show();
        }
    }
}
