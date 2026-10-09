package com.abolfazl260.flightiranbot24;

import java.util.Locale;

/** Immutable metadata copied from the existing repository's airport catalogue. */
public final class AirportEntry {
    public final String code;
    public final String country;
    public final String fa;
    public final String en;
    public final String ar;
    public final String timeZone;

    public AirportEntry(String code, String country, String fa, String en,
                        String ar, String timeZone) {
        this.code = code;
        this.country = country;
        this.fa = fa;
        this.en = en;
        this.ar = ar;
        this.timeZone = timeZone;
    }

    public String nameFor(Locale locale) {
        String language = locale.getLanguage();
        if ("fa".equals(language)) {
            return fa;
        }
        if ("ar".equals(language)) {
            return ar;
        }
        return en;
    }

    public boolean matches(String query) {
        String lower = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        return code.toLowerCase(Locale.ROOT).contains(lower)
                || country.toLowerCase(Locale.ROOT).contains(lower)
                || fa.toLowerCase(Locale.ROOT).contains(lower)
                || en.toLowerCase(Locale.ROOT).contains(lower)
                || ar.toLowerCase(Locale.ROOT).contains(lower)
                || timeZone.toLowerCase(Locale.ROOT).contains(lower);
    }
}
