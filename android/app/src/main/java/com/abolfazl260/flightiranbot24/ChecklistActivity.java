package com.abolfazl260.flightiranbot24;

import android.app.Activity;
import android.content.SharedPreferences;
import android.content.Context;
import android.os.Bundle;
import android.widget.Button;
import android.widget.CheckBox;

/** Fully offline packing checklist stored only on this Android device. */
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
        for (int i = 0; i < KEYS.length; i++) {
            final String key = KEYS[i];
            CheckBox checkBox = findViewById(VIEW_IDS[i]);
            checkBox.setChecked(preferences.getBoolean(key, false));
            checkBox.setOnCheckedChangeListener((button, checked) ->
                    preferences.edit().putBoolean(key, checked).apply());
        }
        Button reset = findViewById(R.id.resetChecklist);
        reset.setOnClickListener(view -> {
            preferences.edit().clear().apply();
            for (int viewId : VIEW_IDS) {
                ((CheckBox) findViewById(viewId)).setChecked(false);
            }
        });
    }
}
