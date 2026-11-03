package com.abolfazl260.flightiranbot24;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.net.URI;
import org.junit.Test;

public final class BotLinksTest {
    @Test
    public void linksUseFixedSecureHosts() {
        assertEquals("t.me", URI.create(BotLinks.BOT).getHost());
        assertEquals("t.me", URI.create(BotLinks.SUPPORT).getHost());
        for (String link : new String[] {BotLinks.BOT, BotLinks.SUPPORT,
                BotLinks.VISA, BotLinks.AIRPORTS, BotLinks.USEFUL}) {
            assertEquals("https", URI.create(link).getScheme());
        }
    }

    @Test
    public void everyDeepLinkTargetsTheKnownBotWithAllowlistedPayload() {
        assertEquals("https://t.me/Flightiranbot?start=visa", BotLinks.VISA);
        assertEquals("https://t.me/Flightiranbot?start=airports", BotLinks.AIRPORTS);
        assertEquals("https://t.me/Flightiranbot?start=useful", BotLinks.USEFUL);
    }

    @Test
    public void visaWatchRouteIsBoundedToKnownBotAndCountryPair() {
        assertEquals("https://t.me/Flightiranbot?start=visa_IR_TR", BotLinks.visaWatch("IR", "TR"));
        try {
            BotLinks.visaWatch("IR", "TR&token=x");
            throw new AssertionError("Must reject malformed destination");
        } catch (IllegalArgumentException expected) {
            // Nothing untrusted is copied into Telegram deep links.
        }
        try {
            BotLinks.visaWatch("ir", "TR");
            throw new AssertionError("Must reject lowercase country code");
        } catch (IllegalArgumentException expected) {
            // Only uppercase ISO-3166 alpha-2 codes are accepted.
        }
    }

    @Test
    public void supportPointsToCurrentAccount() {
        assertTrue(BotLinks.SUPPORT.endsWith("/Advertio_support"));
    }
}
