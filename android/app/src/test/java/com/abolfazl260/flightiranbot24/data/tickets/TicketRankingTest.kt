package com.abolfazl260.flightiranbot24.data.tickets

import org.junit.Assert.*
import org.junit.Test
import com.google.gson.JsonParser

class TicketRankingTest {
    private fun fare(name: String, p: Long, a: Double?, n: Int = 3) =
        TicketFare(name, p, a?.toLong(), -99.0, n, a)

    @Test fun sharedFixtureMatchesFullOrderingAndTopN() {
        val resource = javaClass.getResourceAsStream("/ticket-ranking-v1.json")!!
        val fixture = resource.bufferedReader().use { JsonParser.parseReader(it).asJsonObject }
        val raw = fixture.getAsJsonArray("routes")
        val all = raw.flatMap { route ->
            val row = route.asJsonObject
            val origin = row.get("origin").asString
            row.getAsJsonArray("destinations").map { entry ->
                val f = entry.asJsonObject
                origin to fare(f.get("name").asString, f.get("price_toman").asLong,
                    f.get("average_price_toman").takeUnless { it.isJsonNull }?.asDouble,
                    f.get("average_sample_count").asInt)
            }
        }
        for ((mode,key) in listOf(TicketSort.CHEAPEST to "expected_cheap",TicketSort.DROPS to "expected_drops")) {
            // The UI filters one origin; combine per-origin results using the global contract.
            val rows = all.filter { mode == TicketSort.CHEAPEST || it.second.validDropPercent() != null }
                .filter { it.second.currentToman > 0 }
                .sortedWith(compareBy<Pair<String,TicketFare>> {
                    if (mode == TicketSort.DROPS) -(it.second.validDropPercent() ?: 0.0) else 0.0
                }.thenBy { it.second.currentToman }.thenBy { it.first }.thenBy { it.second.destination })
            assertEquals(fixture.getAsJsonArray(key).map { it.asString },rows.map { it.first+"/"+it.second.destination })
            all.map { it.first }.distinct().forEach { origin ->
                assertEquals(rows.filter { it.first == origin }.map { it.second },
                    rankTicketFares(all.filter { it.first == origin }.map { it.second },mode))
            }
            if (mode == TicketSort.DROPS) assertEquals(
                fixture.getAsJsonArray("expected_percentages").map { it.asDouble },
                rows.map { it.second.validDropPercent() })
        }
        assertEquals(1.3,fare("half",79,80.0).validDropPercent()!!,0.001)
    }

    @Test fun rejectsUnverifiedReductions() {
        listOf(fare("a",10,20.0,2),fare("a",10,0.0),fare("a",10,-20.0),
            fare("a",10,null),fare("a",10,Double.NaN),fare("a",10,Double.POSITIVE_INFINITY),
            fare("a",10,9.0),fare("a",0,20.0)).forEach { assertNull(it.validDropPercent()) }
        assertEquals(33.3, fare("a",2,3.0).validDropPercent()!!,0.001)
    }
    @Test fun filtersAndSortsBothTabsDeterministically() {
        val fares = listOf(fare("Y",80,100.0),fare("X",40,50.0),fare("Z",1,null),
            fare("D",60,100.0),fare("invalid",-1,10.0))
        assertEquals(listOf("D","X","Y"),rankTicketFares(fares,TicketSort.DROPS).map { it.destination })
        assertEquals(listOf("Z","X","D","Y"),rankTicketFares(fares,TicketSort.CHEAPEST).map { it.destination })
        assertEquals(listOf("X"),rankTicketFares(fares,TicketSort.DROPS,"x").map { it.destination })
        assertTrue(rankTicketFares(fares,TicketSort.DROPS,"missing").isEmpty())
    }
}
