package com.abolfazl260.flightiranbot24.data.tickets

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.time.Instant
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class TicketHistoryRepositoryTest {
    private fun fixture() = javaClass.getResourceAsStream("/ticket-history-v1.json")!!.bufferedReader().use {
        JsonParser.parseReader(it).asJsonObject
    }
    private val now = Instant.parse("2026-01-02T13:00:00Z")
    @Test fun sharedFixturePreservesDaysMinimaCountsAndNonInterpolatedGaps() {
        val h=TicketHistoryRepository(null).parse(fixture(),now)!!
        assertEquals(100L,h.minimum);assertEquals(300L,h.maximum);assertEquals(10,h.samples)
        assertEquals(4,h.points.size);assertEquals(2,h.segments.size)
        assertEquals("2025-12-13",h.start.toString());assertFalse(h.stale)
        assertEquals(20L,h.points.last().day.toEpochDay()-h.points.first().day.toEpochDay())
    }
    @Test fun emptySingleFlatAndInvalidDataAreHandledWithoutFabrication() {
        val repo=TicketHistoryRepository(null)
        val empty=fixture().apply { add("points",com.google.gson.JsonArray());add("observed_at",com.google.gson.JsonNull.INSTANCE) }
        assertTrue(repo.parse(empty,now)!!.points.isEmpty());assertNull(repo.parse(empty,now)!!.minimum)
        val single=fixture().apply { val p=getAsJsonArray("points").last();add("points",com.google.gson.JsonArray().apply{add(p)}) }
        assertEquals(1,repo.parse(single,now)!!.points.size);assertTrue(repo.parse(single,now)!!.segments.isEmpty())
        val flat=fixture().apply { getAsJsonArray("points").forEach { it.asJsonObject.addProperty("price_toman",100) } }
        assertEquals(repo.parse(flat,now)!!.minimum,repo.parse(flat,now)!!.maximum)
        for(key in listOf("price_toman","sample_count")) {
            val invalid=fixture().apply { getAsJsonArray("points")[0].asJsonObject.addProperty(key,0) }
            assertNull(repo.parse(invalid,now))
        }
        assertTrue(repo.parse(fixture(),now.plusSeconds(10801))!!.stale)
    }
    @Test fun routeEncodingAndApiFailuresAreExplicit() = runBlocking {
        val calls=mutableListOf<String>()
        val api=object:PublicJsonRepository<JsonObject>{
            override suspend fun fetch(relativePath: String): NetworkResult<JsonObject> {
                calls.add(relativePath);return NetworkResult.Success(fixture())
            }
        }
        TicketHistoryRepository(api).load("A","B")
        assertEquals(listOf("api/v1/tickets/history?origin=A&destination=B"),calls)
        assertTrue(runCatching{TicketHistoryRepository(null).load("A","B")}.isFailure)
    }
}
