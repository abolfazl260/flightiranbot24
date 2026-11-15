package com.abolfazl260.flightiranbot24.data.tickets

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class TicketPriceDateFormatterTest {
    @Test fun formatsUtcTimestampAsTehranLocalJalaliDate() {
        assertEquals(
            "۲۴ آبان ۱۴۰۵، ساعت ۰۷:۳۰",
            formatTicketObservedAt("2026-11-15T04:00:00Z"),
        )
    }

    @Test fun convertsAcrossTehranMidnightAndPersianNewYear() {
        assertEquals(
            "۱ فروردین ۱۴۰۵، ساعت ۰۰:۰۰",
            formatTicketObservedAt("2026-03-20T20:30:00Z"),
        )
    }

    @Test fun invalidTimestampIsNotReturnedAsRawIsoText() {
        assertNull(formatTicketObservedAt("not-a-timestamp"))
    }
}
