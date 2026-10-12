package com.abolfazl260.flightiranbot24;

import android.animation.ObjectAnimator;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Twelve concrete travel-preparation steps grouped into three sections.
 * The original six SharedPreferences keys are deliberately preserved to
 * retain completed tasks when an existing user installs this update.
 */
public final class ChecklistActivity extends Activity {
    static final String PREFS = "travel_checklist";
    static final String[] KEYS = {
        "passport", "visa", "tickets", "boarding", "stay",
        "insurance", "essentials", "emergency",
        "money", "connectivity", "luggage", "transfers"
    };
    static final int[] VIEW_IDS = {
        R.id.checkPassport, R.id.checkVisa, R.id.checkTickets,
        R.id.checkBoarding, R.id.checkStay, R.id.checkInsurance,
        R.id.checkEssentials, R.id.checkEmergency, R.id.checkMoney,
        R.id.checkConnectivity, R.id.checkLuggage, R.id.checkTransfers
    };

    private boolean resetting;
    private ObjectAnimator progressAnimation;

    @Override
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(PersianContext.wrap(base));
    }

    static int completionPercent(int completed, int total) {
        if (total <= 0 || completed < 0 || completed > total) {
            throw new IllegalArgumentException("Invalid checklist progress");
        }
        return Math.round(100f * completed / total);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_checklist);
        UiInsets.apply(this, findViewById(R.id.root));

        SharedPreferences preferences = getSharedPreferences(PREFS, MODE_PRIVATE);
        TextView progress = findViewById(R.id.checklistProgress);
        TextView percentageText = findViewById(R.id.checklistPercent);
        TextView remaining = findViewById(R.id.checklistRemaining);
        ProgressBar progressBar = findViewById(R.id.checklistProgressBar);

        Runnable updateProgress = () -> {
            int completed = 0;
            for (int viewId : VIEW_IDS) {
                if (((CheckBox) findViewById(viewId)).isChecked()) {
                    completed++;
                }
            }

            int percentage = completionPercent(completed, KEYS.length);
            progress.setText(getString(R.string.checklist_progress, completed, KEYS.length));
            percentageText.setText(getString(R.string.checklist_progress_percent, percentage));
            remaining.setText(completed == KEYS.length
                    ? getString(R.string.checklist_completed)
                    : getString(R.string.checklist_remaining, KEYS.length - completed));

            progressBar.setContentDescription(
                    getString(R.string.checklist_percent_description, percentage));
            if (progressAnimation != null) {
                progressAnimation.cancel();
            }
            progressAnimation = ObjectAnimator.ofInt(
                    progressBar, "progress", progressBar.getProgress(), percentage);
            progressAnimation.setDuration(260);
            progressAnimation.start();
        };

        for (int i = 0; i < KEYS.length; i++) {
            final String key = KEYS[i];
            CheckBox checkBox = findViewById(VIEW_IDS[i]);
            checkBox.setChecked(preferences.getBoolean(key, false));
            checkBox.setOnCheckedChangeListener((button, checked) -> {
                if (!resetting) {
                    preferences.edit().putBoolean(key, checked).apply();
                    updateProgress.run();
                }
            });
        }
        updateProgress.run();

        Button reset = findViewById(R.id.resetChecklist);
        reset.setOnClickListener(view -> new AlertDialog.Builder(this)
                .setTitle(R.string.checklist_reset_confirm_title)
                .setMessage(R.string.checklist_reset_confirm_message)
                .setNegativeButton(R.string.checklist_reset_cancel,
                        (dialog, which) -> dialog.dismiss())
                .setPositiveButton(R.string.checklist_reset_confirm, (dialog, which) -> {
                    resetting = true;
                    preferences.edit().clear().apply();
                    for (int viewId : VIEW_IDS) {
                        ((CheckBox) findViewById(viewId)).setChecked(false);
                    }
                    resetting = false;
                    updateProgress.run();
                    Toast.makeText(this, R.string.checklist_reset_done,
                            Toast.LENGTH_SHORT).show();
                })
                .show());
    }

    @Override
    protected void onDestroy() {
        if (progressAnimation != null) {
            progressAnimation.cancel();
        }
        super.onDestroy();
    }
}
