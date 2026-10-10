package com.abolfazl260.flightiranbot24;

import android.content.Context;
import android.content.res.Configuration;
import java.util.Locale;

/** Keep the Android companion app Persian and RTL on every device locale. */
public final class PersianContext {
    private PersianContext() { }

    public static Context wrap(Context base) {
        Configuration config = new Configuration(base.getResources().getConfiguration());
        Locale persian = Locale.forLanguageTag("fa-IR");
        config.setLocale(persian);
        config.setLayoutDirection(persian);
        return base.createConfigurationContext(config);
    }
}
