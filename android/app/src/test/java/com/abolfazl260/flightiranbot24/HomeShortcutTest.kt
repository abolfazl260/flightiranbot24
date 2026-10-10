package com.abolfazl260.flightiranbot24

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HomeShortcutTest {
    @Test
    fun offlineServicesStayNativeAndAvailable() {
        assertEquals(
            listOf(
                HomeDestination.OFFLINE_AIRPORTS,
                HomeDestination.OFFLINE_CHECKLIST,
            ),
            offlineHomeShortcuts.map { it.destination },
        )
    }

    @Test
    fun onlineLinksRemainExplicitHandOffUntilBackendApiExists() {
        val destinations = onlineHomeShortcuts.map { it.destination }
        assertEquals(6, destinations.size)
        assertTrue(destinations.contains(HomeDestination.TELEGRAM_VISA))
        assertTrue(destinations.contains(HomeDestination.SUPPORT))
        assertTrue(destinations.contains(HomeDestination.PRIVACY))
        assertEquals(destinations.size, destinations.distinct().size)
        assertFalse(destinations.any { it.name.contains("CURRENCY") })
    }

    @Test
    fun eachHomeShortcutHasAUniqueDestinationAndStringResource() {
        val all = offlineHomeShortcuts + onlineHomeShortcuts
        assertEquals(8, all.size)
        assertEquals(all.size, all.map { it.destination }.distinct().size)
        assertEquals(all.size, all.map { it.labelRes }.distinct().size)
    }
}
