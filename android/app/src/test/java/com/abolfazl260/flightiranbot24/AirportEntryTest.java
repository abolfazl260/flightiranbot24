package com.abolfazl260.flightiranbot24;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Locale;
import org.junit.Test;

public final class AirportEntryTest {
    private final AirportEntry airport = new AirportEntry(
            "IKA", "IR", "امام خمینی تهران", "Imam Khomeini Tehran",
            "مطار الإمام الخميني", "Asia/Tehran");

    @Test
    public void searchSupportsCodesAndMultipleLanguages() {
        assertTrue(airport.matches("ika"));
        assertTrue(airport.matches("  IKA "));
        assertTrue(airport.matches("Tehran"));
        assertTrue(airport.matches("تهران"));
        assertTrue(airport.matches("الخَميني") == false);
        assertTrue(airport.matches("ایران") == false);
        assertTrue(airport.matches(""));
        assertFalse(airport.matches("Sydney"));
    }

    @Test
    public void returnsNameForPhoneLocale() {
        assertEquals("امام خمینی تهران", airport.nameFor(new Locale("fa")));
        assertEquals("مطار الإمام الخميني", airport.nameFor(new Locale("ar")));
        assertEquals("Imam Khomeini Tehran", airport.nameFor(Locale.US));
    }
}
