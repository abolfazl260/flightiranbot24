package com.abolfazl260.flightiranbot24.data.airports

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.abolfazl260.flightiranbot24.domain.airports.AirportCacheRecord
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class RoomAirportCacheRepositoryTest {
    private val tehran = AirportCacheRecord(
        "IKA", "IR", "Imam Khomeini Airport", "Asia/Tehran"
    )
    private val dubai = AirportCacheRecord(
        "DXB", "AE", "Dubai International", "Asia/Dubai"
    )

    @Test
    fun atomicReplacementDoesNotLeaveOldRowsOrPartialChanges() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val database = Room.inMemoryDatabaseBuilder(
            context, TravelCacheDatabase::class.java
        ).build()
        try {
            val repository = RoomAirportCacheRepository(database)
            repository.replaceCatalog("2026-10-10", listOf(tehran, dubai))
            assertEquals(2, repository.all().size)
            assertEquals(tehran, repository.findByIata("IKA"))

            assertThrows(IllegalArgumentException::class.java) {
                runBlocking {
                    repository.replaceCatalog(
                        "next", listOf(tehran, tehran)
                    )
                }
            }
            assertThrows(IllegalArgumentException::class.java) {
                runBlocking {
                    repository.replaceCatalog(
                        "next", listOf(AirportCacheRecord("BAD!", "IR", "Airport", "Asia/Tehran"))
                    )
                }
            }
            assertThrows(IllegalArgumentException::class.java) {
                runBlocking { repository.replaceCatalog("next", emptyList()) }
            }
            assertEquals(2, repository.all().size)
            assertEquals(tehran, repository.findByIata("IKA"))
            assertNull(repository.findByIata("../"))
            repository.replaceCatalog("next", listOf(dubai))
            assertEquals(listOf(dubai), repository.all())
            assertNull(repository.findByIata("IKA"))
        } finally {
            database.close()
        }
    }

    @Test
    fun reopeningVersionOneDatabasePreservesCachedRows() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val name = "and-003-airport-persistence-test.db"
        context.deleteDatabase(name)
        try {
            val firstDatabase = Room.databaseBuilder(
                context, TravelCacheDatabase::class.java, name
            ).build()
            try {
                RoomAirportCacheRepository(firstDatabase).replaceCatalog(
                    "revision-1", listOf(tehran, dubai)
                )
            } finally {
                firstDatabase.close()
            }
            val reopened = Room.databaseBuilder(
                context, TravelCacheDatabase::class.java, name
            ).build()
            try {
                val existing = RoomAirportCacheRepository(reopened).all()
                assertEquals(2, existing.size)
                assertEquals(listOf(dubai, tehran), existing)
            } finally {
                reopened.close()
            }
        } finally {
            context.deleteDatabase(name)
        }
    }
}
