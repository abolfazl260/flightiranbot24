package com.abolfazl260.flightiranbot24.data.tickets

import kotlin.math.floor

internal enum class TicketSort { CHEAPEST, DROPS }

/** Only positive, observed reductions with at least three historical samples. */
internal fun TicketFare.validDropPercent(): Double? {
    val average = historicalAverage ?: return null
    if (currentToman <= 0 || !average.isFinite() || average <= currentToman ||
        averageSampleCount < 3) return null
    val value = floor((average - currentToman) * 1000.0 / average + 0.5) / 10.0
    return value.takeIf { it.isFinite() && it > 0 }
}

internal fun rankTicketFares(fares: List<TicketFare>, sort: TicketSort, search: String = ""): List<TicketFare> {
    val eligible = fares.filter { it.currentToman > 0 &&
        it.destination.contains(search.trim(), ignoreCase = true) &&
        (sort == TicketSort.CHEAPEST || it.validDropPercent() != null) }
    return if (sort == TicketSort.DROPS) eligible.sortedWith(
        compareByDescending<TicketFare> { it.validDropPercent() }
            .thenBy { it.currentToman }.thenBy { it.destination }
    ) else eligible.sortedWith(compareBy<TicketFare> { it.currentToman }.thenBy { it.destination })
}
