package com.abolfazl260.flightiranbot24.data.tickets

import org.junit.Assert.*
import org.junit.Test

class TicketRankingTest {
    private fun fare(name: String, p: Long, a: Double?, n: Int = 3) =
        TicketFare(name, p, a?.toLong(), -99.0, n, a)

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
