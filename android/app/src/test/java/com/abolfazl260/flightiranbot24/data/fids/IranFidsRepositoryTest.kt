package com.abolfazl260.flightiranbot24.data.fids

import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class IranFidsRepositoryTest {
    private val repo = IranFidsRepository(null)
    private fun json(value: String) = JsonParser.parseString(value).asJsonObject

    private fun sample(additional: String = "") = json(
        """{
          "airport": "THR",
          "direction": "departures",
          "source": "Iran Airports and Air Navigation Company FIDS",
          "fetched_at": "2026-10-31T15:00:00Z",
          "source_updated_at": null,
          "freshness": "unverified",
          "flights": [{
            "flight_number": "IR123", "airline": "ایران ایر",
            "city": "مشهد", "scheduled_time": "13:25",
            "status": "طبق برنامه", "terminal": null, "gate": null
          }]
        }""".replace("\"status\": \"طبق برنامه\",", "\"status\": \"طبق برنامه\", $additional")
    )

    @Test fun acceptsWhitelistedBoardWithoutInventingTerminal() {
        val board = repo.parse(sample(), "THR", FlightDirection.DEPARTURES)
        assertEquals("THR", board?.airport)
        assertEquals(1, board?.flights?.size)
        assertEquals("IR123", board?.flights?.get(0)?.flightNumber)
        assertNull(board?.flights?.get(0)?.gate)
        assertTrue(board?.sourceTimeUnverified == true)
        assertTrue(board?.sourceIsOld == true)
    }

    @Test fun mismatchedAirportOrDirectionRejected() {
        assertNull(repo.parse(sample(), "MHD", FlightDirection.DEPARTURES))
        assertNull(repo.parse(sample(), "THR", FlightDirection.ARRIVALS))
    }

    @Test fun invalidOrUnverifiedSourceCannotBecomeFlightList() {
        val raw = sample()
        raw.remove("flights")
        assertNull(repo.parse(raw, "THR", FlightDirection.DEPARTURES))
        assertNull(repo.parse(json("""{"flights":[]}"""), "THR", FlightDirection.DEPARTURES))
    }

    @Test fun emptyVerifiedResponseIsEmptyBoardNotAnError() {
        val raw = sample()
        raw.add("flights", JsonParser.parseString("[]"))
        val board = repo.parse(raw, "THR", FlightDirection.DEPARTURES)
        assertTrue(board != null)
        assertTrue(board?.flights?.isEmpty() == true)
    }

    @Test fun declaredFreshnessNeedsProviderTimestamp() {
        val raw = sample()
        raw.addProperty("freshness", "reported")
        assertNull(repo.parse(raw, "THR", FlightDirection.DEPARTURES))
        raw.addProperty("source_updated_at", "2026-10-31T14:59:00Z")
        assertFalse(repo.parse(raw, "THR", FlightDirection.DEPARTURES)?.sourceTimeUnverified ?: true)
    }

    @Test fun noUnsupportedAirportWasInadvertentlyIncluded() {
        assertTrue(iranFidsAirports.any { it.code == "THR" })
        assertFalse(iranFidsAirports.any { it.code == "LHR" || it.code == "IKA" })
    }
}
