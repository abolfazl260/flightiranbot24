package com.abolfazl260.flightiranbot24.domain.airports

/** A cached, revisioned *public* airport row: never user-specific content. */
internal data class AirportCacheRecord(
    val iata: String,
    val country: String,
    val name: String,
    val timezone: String,
)

internal interface AirportCacheRepository {
    /** Atomically publish the complete validated snapshot. */
    suspend fun replaceCatalog(dataVersion: String, rows: List<AirportCacheRecord>)
    suspend fun all(): List<AirportCacheRecord>
    suspend fun findByIata(iata: String): AirportCacheRecord?
}
