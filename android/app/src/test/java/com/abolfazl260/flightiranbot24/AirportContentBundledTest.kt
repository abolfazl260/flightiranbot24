package com.abolfazl260.flightiranbot24

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/** The real checked-in GitHub JSON is also bundled for offline Android access. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class AirportContentBundledTest {
    private val context: Context
        get() = ApplicationProvider.getApplicationContext()

    private fun bundled(path: String): String =
        context.assets.open(path).bufferedReader().use { it.readText() }

    @Test fun onlySourceBackedIkaIsListed() {
        val index = AirportContentParser.parseIndex(bundled("airport-index.v1.json"))
        assertEquals(listOf("IKA"), index.airports.map { it.iata })
        val names = readBundledAirportNames(context)
        assertEquals("امام خمینی تهران", names["IKA"]?.name)
        assertTrue(filterAirports(listOf(names.getValue("IKA")), "امام").isNotEmpty())
    }

    @Test fun ikaHasFourteenPublishedSectionsAndHidesUnverifiedMediaAndReviews() {
        val page = AirportContentParser.parseDetail(bundled("details/IKA.v1.json"), "IKA")
        assertEquals(14, page.sections.size)
        assertEquals("baggage-rules", page.sections.first().id)
        assertTrue(page.sections.any { it.id == "flight-status" })
        assertTrue(page.sections.any { it.id == "airport-map" })
        assertTrue(page.sections.any { it.id == "terminals" })
        assertFalse(page.sections.any { it.id == "airport-videos" })
        assertFalse(page.sections.any { it.id == "traveler-experiences" })
        assertTrue(page.sections.all { it.sources.isNotEmpty() && it.blocks.isNotEmpty() })
        assertTrue(page.sections.any { it.subtitle != null })
    }
}
