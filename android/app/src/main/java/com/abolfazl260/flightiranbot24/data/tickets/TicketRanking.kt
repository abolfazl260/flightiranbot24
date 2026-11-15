package com.abolfazl260.flightiranbot24.data.tickets

import kotlin.math.floor

internal enum class TicketSort { CHEAPEST, DROPS, ALL }

/** Only positive, observed reductions with at least three historical samples. */
internal fun TicketFare.validDropPercent(): Double? {
    val average = historicalAverage ?: return null
    if (currentToman <= 0 || currentToman > 1_000_000_000_000L || !average.isFinite() ||
        average > 1e12 || average <= currentToman ||
        averageSampleCount !in 3..100000) return null
    val value = floor((average - currentToman) * 1000.0 / average + 0.5) / 10.0
    return value.takeIf { it.isFinite() && it > 0 }
}

internal fun rankTicketFares(fares: List<TicketFare>, sort: TicketSort, search: String = ""): List<TicketFare> {
    val eligible = fares.filter { it.currentToman in 1..1_000_000_000_000L &&
        it.destination.contains(search.trim(), ignoreCase = true) &&
        (sort != TicketSort.DROPS || it.validDropPercent() != null) }
    return when (sort) {
        TicketSort.DROPS -> eligible.sortedWith(
            compareByDescending<TicketFare> { it.validDropPercent() }
                .thenBy { it.currentToman }.thenBy { it.destination }
        )
        TicketSort.CHEAPEST -> eligible.sortedWith(
            compareBy<TicketFare> { it.currentToman }.thenBy { it.destination }
        )
        // Keep the source order when the user explicitly asks to see every destination.
        TicketSort.ALL -> eligible
    }
}
