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
    fun eachCompiledFlavorKeepsTheExpectedNoncollidingId() {
        val expected = when (BuildConfig.APP_ENVIRONMENT) {
            "development" -> "com.abolfazl260.flightiranbot24.dev.debug"
            "staging" -> "com.abolfazl260.flightiranbot24.staging.debug"
            "production" -> "com.abolfazl260.flightiranbot24.debug"
            else -> throw AssertionError("Unexpected environment")
        }
        assertEquals(expected, BuildConfig.APPLICATION_ID)
        val environment = EnvironmentSettings.fromBuild()
        assertEquals(BuildConfig.APP_ENVIRONMENT, environment.name)
        assertEquals(BuildConfig.API_BASE_URL, environment.apiOrigin)
        assertEquals(BuildConfig.APP_ENVIRONMENT == "production", environment.isProduction)
    }

    @Test
    fun unconfiguredEnvironmentsDoNotMakeUpAnApiOrigin() {
        val environment = EnvironmentSettings("staging", "")
        assertFalse(environment.isConfigured)
        assertNull(environment.publicApi())
        val configured = EnvironmentSettings(
            "development", "https://dev.example.org/"
        )
        assertTrue(configured.isConfigured)
        assertNotNull(configured.publicApi())
    }

    @Test
    fun rejectsUnknownEnvironmentsAndInsecureNetworkUrls() {
        assertThrows(IllegalArgumentException::class.java) {
            EnvironmentSettings("unknown", "")
        }
        for (bad in listOf(
            "http://api.example.com/", "https://user:pass@api.example.com/",
            "https://example.com/route", "https://example.com/?token=1",
        )) {
            assertThrows(IllegalArgumentException::class.java) {
                EnvironmentSettings("production", bad)
            }
        }
    }
}
