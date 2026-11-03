package com.abolfazl260.flightiranbot24;

import android.animation.ObjectAnimator;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.os.Bundle;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.ImageView;
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


    /**
     * The transparent WebP atlas is a 5 x 3 grid of the artwork approved for
     * the travel checklist. Cropping in memory keeps the APK small and avoids
     * repeated copies of the same images in different density folders.
     *
     * Cell order: passport, visa, tickets, boarding pass, hotel;
     * insurance, medication, emergency call, money, SIM;
     * luggage, airport transfer, calendar, security, luggage settings.
     */
    private void applyChecklistArtwork() {
        Bitmap atlas = BitmapFactory.decodeResource(getResources(), R.drawable.checklist_icons_atlas);
        if (atlas == null || atlas.getWidth() % 5 != 0 || atlas.getHeight() % 3 != 0) {
            return;
        }
        final int[] cells = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
        for (int i = 0; i < VIEW_IDS.length; i++) {
            CheckBox box = findViewById(VIEW_IDS[i]);
            Drawable icon = iconFromAtlas(atlas, cells[i], 52);
            box.setCompoundDrawablesRelative(null, null, icon, null);
        }
        setArtwork(findViewById(R.id.checklistHeaderIcon), atlas, 14);
        setArtwork(findViewById(R.id.checklistDocumentsIcon), atlas, 0);
        setArtwork(findViewById(R.id.checklistHealthIcon), atlas, 5);
        setArtwork(findViewById(R.id.checklistEssentialsIcon), atlas, 10);
    }

    private void setArtwork(ImageView view, Bitmap atlas, int cell) {
        view.setImageDrawable(iconFromAtlas(atlas, cell, 56));
    }

    private Drawable iconFromAtlas(Bitmap atlas, int cell, int sizeDp) {
        int width = atlas.getWidth() / 5;
        int height = atlas.getHeight() / 3;
        Bitmap cropped = Bitmap.createBitmap(
                atlas, (cell % 5) * width, (cell / 5) * height, width, height);
        BitmapDrawable drawable = new BitmapDrawable(getResources(), cropped);
        drawable.setFilterBitmap(true);
        int px = Math.round(sizeDp * getResources().getDisplayMetrics().density);
        drawable.setBounds(0, 0, px, px);
        return drawable;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_checklist);
        UiInsets.apply(this, findViewById(R.id.root));
        applyChecklistArtwork();

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
