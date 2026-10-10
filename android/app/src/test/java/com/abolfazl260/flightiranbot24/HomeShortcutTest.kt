package com.abolfazl260.flightiranbot24

import com.abolfazl260.flightiranbot24.data.LocalHomeRepository
import com.abolfazl260.flightiranbot24.domain.HomeDestination
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HomeShortcutTest {
    @Test
    fun offlineServicesStayNativeAndAvailable() = runBlocking {
        assertEquals(
            listOf(
                HomeDestination.OFFLINE_AIRPORTS,
                HomeDestination.OFFLINE_CHECKLIST,
            ),
            LocalHomeRepository().loadHomeSections().offline,
        )
    }

    @Test
    fun onlineLinksRemainExplicitHandOffUntilBackendApiExists() = runBlocking {
        val destinations = LocalHomeRepository().loadHomeSections().online
        assertEquals(6, destinations.size)
        assertTrue(destinations.contains(HomeDestination.TELEGRAM_VISA))
        assertTrue(destinations.contains(HomeDestination.SUPPORT))
        assertTrue(destinations.contains(HomeDestination.PRIVACY))
        assertEquals(destinations.size, destinations.distinct().size)
        assertFalse(destinations.any { it.name.contains("CURRENCY") })
    }

    @Test
    fun eachHomeShortcutHasAUniqueDestination() = runBlocking {
        val data = LocalHomeRepository().loadHomeSections()
        val all = data.offline + data.online
        assertEquals(8, all.size)
        assertEquals(all.size, all.distinct().size)
    }
}
