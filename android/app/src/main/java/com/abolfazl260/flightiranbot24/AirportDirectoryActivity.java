package com.abolfazl260.flightiranbot24;

import android.app.Activity;
import android.content.Context;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Offline, searchable airport IATA and timezone directory. No network permission. */
public final class AirportDirectoryActivity extends Activity {
    private final List<AirportEntry> airports = new ArrayList<>();
    private LinearLayout results;
    private TextView count;
    private TextView empty;

    @Override
    protected void attachBaseContext(Context base) {
        super.attachBaseContext(PersianContext.wrap(base));
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_airports);
        UiInsets.apply(this, findViewById(R.id.root));
        results = findViewById(R.id.airportResults);
        count = findViewById(R.id.airportCount);
        empty = findViewById(R.id.emptyAirports);

        try (InputStream stream = getAssets().open("airports.json");
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int length;
            while ((length = stream.read(buffer)) != -1) {
                output.write(buffer, 0, length);
            }
            JSONArray data = new JSONArray(output.toString("UTF-8"));
            for (int i = 0; i < data.length(); i++) {
                JSONObject value = data.getJSONObject(i);
                JSONObject names = value.getJSONObject("names");
                airports.add(new AirportEntry(
                        value.getString("code"),
                        value.getString("country"),
                        names.getString("fa"),
                        names.getString("en"),
                        names.getString("ar"),
                        value.getString("timezone")
                ));
            }
        } catch (Exception exception) {
            count.setText(R.string.airports_unavailable);
            empty.setVisibility(View.VISIBLE);
            return;
        }

        EditText search = findViewById(R.id.airportSearch);
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start,
                                                      int n, int after) { }
            @Override public void onTextChanged(CharSequence s, int start,
                                                int before, int n) {
                render(s.toString());
            }
            @Override public void afterTextChanged(Editable s) { }
        });
        render("");
    }

    private void render(String query) {
        results.removeAllViews();
        int visible = 0;
        Locale locale = getResources().getConfiguration().getLocales().get(0);
        for (AirportEntry airport : airports) {
            if (!airport.matches(query)) {
                continue;
            }
            visible++;
            TextView card = new TextView(this);
            card.setText(getString(R.string.airport_item,
                    airport.nameFor(locale), airport.code, airport.country, airport.timeZone));
            card.setTextSize(16);
            card.setTextColor(getColor(R.color.navy));
            card.setPadding(dp(16), dp(12), dp(16), dp(12));
            card.setBackgroundResource(R.drawable.airport_card);
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT);
            params.bottomMargin = dp(10);
            results.addView(card, params);
        }
        count.setText(getString(R.string.airport_count, visible, airports.size()));
        empty.setVisibility(visible == 0 ? View.VISIBLE : View.GONE);
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}
