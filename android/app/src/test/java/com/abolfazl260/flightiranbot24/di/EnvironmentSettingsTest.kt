package com.abolfazl260.flightiranbot24.di

import com.abolfazl260.flightiranbot24.BuildConfig
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class EnvironmentSettingsTest {
    @Test
    fun singleDebugPackageAndConfiguredApi() {
        assertEquals("com.abolfazl260.flightiranbot24.debug", BuildConfig.APPLICATION_ID)
        val environment = EnvironmentSettings.fromBuild()
        assertEquals(BuildConfig.API_BASE_URL, environment.apiOrigin)
    }

    @Test
    fun unconfiguredApiNeverInventsAnOrigin() {
        val environment = EnvironmentSettings("")
        assertFalse(environment.isConfigured)
        assertNull(environment.publicApi())
        val configured = EnvironmentSettings("https://api.example.org/")
        assertTrue(configured.isConfigured)
        assertNotNull(configured.publicApi())
    }

    @Test
    fun rejectsInsecureNetworkUrls() {
        for (bad in listOf(
            "http://api.example.com/", "https://user:pass@api.example.com/",
            "https://example.com/route", "https://example.com/?token=1",
        )) {
            assertThrows(IllegalArgumentException::class.java) {
                EnvironmentSettings(bad)
            }
        }
    }
}
