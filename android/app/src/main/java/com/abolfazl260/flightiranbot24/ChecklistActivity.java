package com.abolfazl260.flightiranbot24;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.TextView;
import android.widget.Toast;

/** Offline checklist: retains saved preferences across upgrades, without sync or data loss. */
public final class ChecklistActivity extends Activity {
    private static final String PREFS = "travel_checklist";
    private static final String[] KEYS = {
        "passport", "visa", "tickets", "insurance", "money", "essentials"
    };
    private static final int[] VIEW_IDS = {
        R.id.checkPassport, R.id.checkVisa, R.id.checkTickets,
        R.id.checkInsurance, R.id.checkMoney, R.id.checkEssentials
    };

    @Override
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(PersianContext.wrap(base));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_checklist);
        UiInsets.apply(this, findViewById(R.id.root));
        SharedPreferences preferences = getSharedPreferences(PREFS, MODE_PRIVATE);
        TextView progress = findViewById(R.id.checklistProgress);
        Runnable updateProgress = () -> {
            int checked = 0;
            for (int viewId : VIEW_IDS) {
                if (((CheckBox) findViewById(viewId)).isChecked()) {
                    checked++;
                }
            }
            progress.setText(getString(R.string.checklist_progress, checked, KEYS.length));
        };

        for (int i = 0; i < KEYS.length; i++) {
            final String key = KEYS[i];
            CheckBox checkBox = findViewById(VIEW_IDS[i]);
            checkBox.setChecked(preferences.getBoolean(key, false));
            checkBox.setOnCheckedChangeListener((button, checked) -> {
                preferences.edit().putBoolean(key, checked).apply();
                updateProgress.run();
            });
        }
        updateProgress.run();

        Button reset = findViewById(R.id.resetChecklist);
        reset.setOnClickListener(view -> new AlertDialog.Builder(this)
                .setTitle(R.string.checklist_reset_confirm_title)
                .setMessage(R.string.checklist_reset_confirm_message)
                .setNegativeButton(R.string.checklist_reset_cancel, (dialog, which) -> dialog.dismiss())
                .setPositiveButton(R.string.checklist_reset_confirm, (dialog, which) -> {
                    preferences.edit().clear().apply();
                    for (int viewId : VIEW_IDS) {
                        ((CheckBox) findViewById(viewId)).setChecked(false);
                    }
                    updateProgress.run();
                    Toast.makeText(this, R.string.checklist_reset_done, Toast.LENGTH_SHORT).show();
                })
                .show());
    }
}
