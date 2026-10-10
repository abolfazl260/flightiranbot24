package com.abolfazl260.flightiranbot24

import org.junit.Assert.assertEquals
import org.junit.Test

class AirportSearchTest {
    private val airports = listOf(
        AirportRow("IKA", "امام خمینی تهران", "IR", "Asia/Tehran", listOf("Tehran")),
        AirportRow("MHD", "مشهد", "IR", "Asia/Tehran", listOf("Mashhad")),
        AirportRow("DXB", "دبی", "AE", "Asia/Dubai", listOf("Dubai")),
    )

    @Test
    fun matchesPersianVariantsAndLatinIataWithoutChangingDisplayLanguage() {
        assertEquals(listOf("IKA"), filterAirports(airports, "تهران").map { it.code })
        assertEquals(listOf("MHD"), filterAirports(airports, "mhd").map { it.code })
        assertEquals(listOf("DXB"), filterAirports(airports, "Dubai").map { it.code })
        assertEquals(listOf("DXB"), filterAirports(airports, "دبي").map { it.code })
        assertEquals(emptyList<AirportRow>(), filterAirports(airports, "not-found"))
    }

    @Test
    fun noSearchReturnsAllRecordsAndNeverMutatesSource() {
        val snapshot = airports.toList()
        assertEquals(3, filterAirports(airports, "").size)
        assertEquals(snapshot, airports)
    }
}
