package com.abolfazl260.flightiranbot24.data.tickets

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TicketPricesRepositoryTest {
    private val document = """
        {"currency":"TOMAN","observed_at":"2026-10-11T15:00:00+00:00","stale":false,
         "routes":[{"origin":"تهران","destinations":[
           {"name":"کیش","price_toman":4500000,"average_price_toman":5000000,
            "change_percent":-10.0,"average_sample_count":5},
           {"name":"تبریز","price_toman":2500000,"average_price_toman":null,
            "change_percent":null,"average_sample_count":0}]}]}
    """.trimIndent()

    @Test fun correctFareAndMissingAverage() {
        val data = TicketPricesRepository(null).parse(JsonParser.parseString(document).asJsonObject)!!
        assertFalse(data.stale)
        assertEquals("تهران", data.origins.single().city)
        assertEquals(4500000L, data.origins.single().fares.first().currentToman)
        assertEquals(5000000L, data.origins.single().fares.first().averageToman)
        assertEquals(-10.0, data.origins.single().fares.first().differencePercent!!, 0.01)
        assertNull(data.origins.single().fares.last().averageToman)
    }

    @Test fun noApiNeverSendsRequest() = runBlocking {
        assertEquals(TicketPricesResult.Unconfigured, TicketPricesRepository(null).load())
    }

    @Test fun rejectsWrongCurrency() {
        assertNull(TicketPricesRepository(null).parse(JsonParser.parseString("{}").asJsonObject))
        assertNull(TicketPricesRepository(null).parse(
            JsonParser.parseString(document.replace("\"TOMAN\"", "\"USD\"")).asJsonObject
        ))
    }

    @Test fun callsVersionedEndpointAndHandlesFailure() = runBlocking {
        val calls = mutableListOf<String>()
        val api = object : PublicJsonRepository<JsonObject> {
            override suspend fun fetch(relativePath: String): NetworkResult<JsonObject> {
                calls.add(relativePath)
                return NetworkResult.Success(JsonParser.parseString(document).asJsonObject)
            }
        }
        assertTrue(TicketPricesRepository(api).load() is TicketPricesResult.Ready)
        assertEquals(listOf("api/v1/tickets/prices"), calls)
        val failing = object : PublicJsonRepository<JsonObject> {
            override suspend fun fetch(relativePath: String) = NetworkResult.ConnectionFailure
        }
        assertEquals(TicketPricesResult.Failed, TicketPricesRepository(failing).load())
    }
}
