package com.abolfazl260.flightiranbot24

import org.junit.Assert.assertTrue
import org.junit.Assert.assertFalse
import org.junit.Test

class FidsWebNavigationTest {
    @Test fun officialHttpsPagesAndFragmentsStayInTheApp() {
        assertTrue(isAllowedFidsNavigation("https://fids.airport.ir/"))
        assertTrue(isAllowedFidsNavigation("https://fids.airport.ir/#arrivals"))
        assertTrue(isAllowedFidsNavigation("https://fids.airport.ir/other?airport=THR"))
        assertTrue(isAllowedFidsNavigation("https://FIDS.AIRPORT.IR:443/"))
    }

    @Test fun externalAndUnsafeDestinationsNeverOpenInsideWebView() {
        listOf(
            "http://fids.airport.ir/",
            "https://fids.airport.ir.evil.example/",
            "https://evil.example/fids.airport.ir",
            "https://airport.ir/",
            "https://fids.airport.ir:8080/",
            "https://name:password@fids.airport.ir/",
            "javascript:alert(1)",
            "file:///android_asset/test.html",
            "intent://fids.airport.ir/",
            "https://fids.airport.ir\\@evil.example/",
            "not a url",
        ).forEach { assertFalse("Unsafe page allowed: $it", isAllowedFidsNavigation(it)) }
    }

    @Test fun serverAndAccessFailuresHaveDistinctUserMessages() {
        assertTrue(fidsHttpStatusMessage(403).contains("دسترسی"))
        assertTrue(fidsHttpStatusMessage(404).contains("پیدا نشد"))
        assertTrue(fidsHttpStatusMessage(429).contains("درخواست"))
        assertTrue(fidsHttpStatusMessage(500).contains("سرور"))
        assertTrue(fidsHttpStatusMessage(504).contains("تأخیر"))
    }
}
