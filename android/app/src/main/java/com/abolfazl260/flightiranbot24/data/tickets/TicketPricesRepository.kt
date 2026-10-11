package com.abolfazl260.flightiranbot24.data.tickets

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject

internal data class TicketFare(
    val destination: String,
    val currentToman: Long,
    val averageToman: Long?,
    val differencePercent: Double?,
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

    internal fun parse(payload: JsonObject): TicketPriceSnapshot? = runCatching {
        if (payload.get("currency")?.asString != "TOMAN") return null
        val observed = payload.get("observed_at")?.asString
            ?.takeIf { it.length >= 19 } ?: return null
        val stale = payload.get("stale")?.asBoolean ?: false
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
                    val price = item.get("price_toman")?.asLong
                        ?.takeIf { it > 0L } ?: return@runCatching null
                    val average = item.get("average_price_toman")
                        ?.takeUnless { it.isJsonNull }?.asLong?.takeIf { it > 0L }
                    val movement = item.get("change_percent")
                        ?.takeUnless { it.isJsonNull }?.asDouble?.takeIf { it.isFinite() }
                    TicketFare(name, price, average, if (average == null) null else movement)
                }.getOrNull()
            }
            if (fares.isEmpty()) null else TicketOrigin(city, fares)
        }
        if (origins.isEmpty()) return null
        TicketPriceSnapshot(origins, observed, stale)
    }.getOrNull()
}
