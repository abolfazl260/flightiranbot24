package com.abolfazl260.flightiranbot24.data.tickets

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject
import java.time.Duration
import java.time.Instant
import java.time.OffsetDateTime

internal data class TicketFare(
    val destination: String,
    val currentToman: Long,
    val averageToman: Long?,
    val differencePercent: Double?,
    val averageSampleCount: Int = 0,
    val historicalAverage: Double? = averageToman?.toDouble(),
)
internal data class TicketOrigin(val city: String, val fares: List<TicketFare>)
internal data class TicketPriceSnapshot(
    val origins: List<TicketOrigin>,
    val observedAt: String,
    val stale: Boolean,
)
internal sealed interface TicketPricesResult {
    data class Ready(val value: TicketPriceSnapshot) : TicketPricesResult
    data object Unconfigured : TicketPricesResult
    data object Failed : TicketPricesResult
}

/** The same sanitized feed as the bot, never direct access to the ticket provider. */
internal class TicketPricesRepository(private val api: PublicJsonRepository<JsonObject>?) {
    suspend fun load(): TicketPricesResult {
        val endpoint = api ?: return TicketPricesResult.Unconfigured
        return when (val result = endpoint.fetch("api/v1/tickets/prices")) {
            is NetworkResult.Success -> parse(result.value)
                ?.let(TicketPricesResult::Ready) ?: TicketPricesResult.Failed
            else -> TicketPricesResult.Failed
        }
    }

    internal fun parse(payload: JsonObject): TicketPriceSnapshot? {
        return runCatching {
        if (payload.get("currency")?.asString != "TOMAN") return null
        val observed = payload.get("observed_at")?.asString ?: return null
        val observedAt = runCatching { OffsetDateTime.parse(observed).toInstant() }.getOrNull()
            ?: return null
        val age = Duration.between(observedAt, Instant.now())
        if (age.isNegative && age.abs() > Duration.ofMinutes(5)) return null
        val publishedStale = payload.get("stale")?.takeIf { it.isJsonPrimitive && it.asJsonPrimitive.isBoolean }
            ?.asBoolean ?: return null
        val stale = publishedStale || age > Duration.ofHours(3)
        val routes = payload.get("routes")?.takeIf { it.isJsonArray }?.asJsonArray ?: return null
        val origins = routes.take(150).mapNotNull { route ->
            if (!route.isJsonObject) return@mapNotNull null
            val row = route.asJsonObject
            val city = row.get("origin")?.asString?.trim()
                ?.takeIf { it.isNotEmpty() } ?: return@mapNotNull null
            val destinations = row.get("destinations")?.takeIf { it.isJsonArray }?.asJsonArray
                ?: return@mapNotNull null
            val fares = destinations.take(150).mapNotNull { element ->
                runCatching {
                    if (!element.isJsonObject) return@runCatching null
                    val item = element.asJsonObject
                    val name = item.get("name")?.asString?.trim()
                        ?.takeIf { it.isNotEmpty() } ?: return@runCatching null
                    fun numeric(key: String): Double? = runCatching {
                        item.get(key)?.takeIf { it.isJsonPrimitive && it.asJsonPrimitive.isNumber }
                            ?.asDouble?.takeIf { it.isFinite() }
                    }.getOrNull()
                    val price = numeric("price_toman")
                        ?.takeIf { it > 0.0 && it <= 1000000000000.0 && it % 1.0 == 0.0 }
                        ?.toLong() ?: return@runCatching null
                    val average = (if (item.has("historical_average_toman")) numeric("historical_average_toman")
                        else numeric("average_price_toman"))?.takeIf { it > 0.0 && it <= 1e12 }
                    val samples = numeric("average_sample_count")
                        ?.takeIf { it >= 0 && it % 1.0 == 0.0 && it <= Int.MAX_VALUE }
                        ?.toInt() ?: 0
                    val fare = TicketFare(name, price, average?.toLong(), null, samples, average)
                    fare.copy(differencePercent = fare.validDropPercent()?.let { -it })
                }.getOrNull()
            }
            if (fares.isEmpty()) null else TicketOrigin(city, fares)
        }
        if (origins.isEmpty()) return null
        TicketPriceSnapshot(origins, observed, stale)
        }.getOrNull()
    }
}
