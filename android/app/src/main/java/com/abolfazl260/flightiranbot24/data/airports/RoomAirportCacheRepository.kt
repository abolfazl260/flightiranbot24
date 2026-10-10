package com.abolfazl260.flightiranbot24.data.airports

import androidx.room.withTransaction
import com.abolfazl260.flightiranbot24.domain.airports.AirportCacheRecord
import com.abolfazl260.flightiranbot24.domain.airports.AirportCacheRepository
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

internal class RoomAirportCacheRepository(
    private val database: TravelCacheDatabase,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
) : AirportCacheRepository {
    private companion object {
        val IATA = Regex("[A-Z]{3}")
        val DATA_REVISION = Regex("[A-Za-z0-9._-]{1,64}")
    }

    override suspend fun replaceCatalog(dataVersion: String, rows: List<AirportCacheRecord>) {
        require(DATA_REVISION.matches(dataVersion)) { "Invalid data revision" }
        require(rows.isNotEmpty()) { "Empty catalogue cannot replace offline data" }
        require(rows.map { it.iata }.distinct().size == rows.size) {
            "Duplicate IATA codes"
        }
        val entities = rows.map { airport ->
            require(IATA.matches(airport.iata)) { "Invalid IATA code" }
            require(
                airport.name.isNotBlank() && airport.country.isNotBlank() &&
                    airport.timezone.isNotBlank()
            ) { "Incomplete airport entry" }
            CachedAirportEntity(
                airport.iata,
                airport.country,
                airport.name,
                airport.timezone,
                dataVersion,
            )
        }
        withContext(ioDispatcher) {
            // An interrupted/invalid import never leaves a partly replaced cache.
            database.withTransaction {
                database.airportCacheDao().clear()
                database.airportCacheDao().upsertAll(entities)
            }
        }
    }

    override suspend fun all(): List<AirportCacheRecord> = withContext(ioDispatcher) {
        database.airportCacheDao().all().map { it.toDomain() }
    }

    override suspend fun findByIata(iata: String): AirportCacheRecord? {
        if (!IATA.matches(iata)) return null
        return withContext(ioDispatcher) {
            database.airportCacheDao().findByIata(iata)?.toDomain()
        }
    }

    private fun CachedAirportEntity.toDomain() = AirportCacheRecord(
        iata = iata, country = country, name = name, timezone = timezone
    )
}
