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
        assertEquals("github.com", URI.create(BotLinks.PRIVACY).getHost());
        for (String link : new String[] {BotLinks.BOT, BotLinks.SUPPORT, BotLinks.PRIVACY}) {
            assertEquals("https", URI.create(link).getScheme());
        }
    }

    @Test
    public void supportPointsToCurrentAccount() {
        assertTrue(BotLinks.SUPPORT.endsWith("/Advertio_support"));
    }
}
