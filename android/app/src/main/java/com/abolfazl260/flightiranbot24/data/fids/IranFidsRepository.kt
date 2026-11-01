package com.abolfazl260.flightiranbot24.data.fids

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import java.time.Duration
import java.time.Instant
import java.time.OffsetDateTime

internal data class FidsAirport(val code: String, val name: String)
internal val iranFidsAirports = listOf(
    FidsAirport("THR", "تهران مهرآباد"), FidsAirport("MHD", "مشهد"),
    FidsAirport("SYZ", "شیراز"), FidsAirport("IFN", "اصفهان"),
    FidsAirport("TBZ", "تبریز"), FidsAirport("AWZ", "اهواز"),
    FidsAirport("BND", "بندرعباس"), FidsAirport("KER", "کرمان"),
    FidsAirport("ZAH", "زاهدان"), FidsAirport("OMH", "ارومیه"),
)

internal enum class FlightDirection(val path: String, val label: String) {
    DEPARTURES("departures", "خروجی"),
    ARRIVALS("arrivals", "ورودی")
}

internal data class IranFlight(
    val flightNumber: String,
    val airline: String?,
    val city: String,
    val scheduledTime: String,
    val estimatedTime: String?,
    val actualTime: String?,
    val status: String?,
    val terminal: String?,
    val gate: String?
)

internal data class IranFidsBoard(
    val airport: String,
    val direction: FlightDirection,
    val fetchedAt: String,
    val sourceUpdatedAt: String?,
    val sourceTimeUnverified: Boolean,
    val flights: List<IranFlight>
) {
    val sourceIsOld: Boolean
        get() = sourceUpdatedAt?.let { source ->
            runCatching { Duration.between(OffsetDateTime.parse(source).toInstant(), Instant.now()) >
                Duration.ofMinutes(15) }.getOrDefault(true)
        } ?: true
}

internal sealed interface IranFidsResult {
    data class Ready(val board: IranFidsBoard) : IranFidsResult
    data object Unavailable : IranFidsResult
}

/**
 * Only the first-party HTTPS Worker can be called from Android.
 * No FIDS website, browser, WebView, HTML scraper, provider key or direct
 * third-party host is allowed in the APK. No persistent flight-state cache.
 */
internal class IranFidsRepository(private val api: PublicJsonRepository<JsonObject>?) {
    suspend fun load(airport: String, direction: FlightDirection): IranFidsResult {
        if (api == null || iranFidsAirports.none { it.code == airport }) return IranFidsResult.Unavailable
        return when (val result = api.fetch("api/v1/iran/fids/" + airport + "/" + direction.path)) {
            is NetworkResult.Success -> parse(result.value, airport, direction)
                ?.let(IranFidsResult::Ready) ?: IranFidsResult.Unavailable
            else -> IranFidsResult.Unavailable
        }
    }

    internal fun parse(source: JsonObject, airport: String, direction: FlightDirection): IranFidsBoard? =
        runCatching {
            if (source.str("airport") != airport ||
                source.str("direction") != direction.path ||
                source.str("source") != "Iran Airports and Air Navigation Company FIDS") return null
            val fetched = source.str("fetched_at") ?: return null
            val fetchedTime = OffsetDateTime.parse(fetched).toInstant()
            if (fetchedTime.isAfter(Instant.now().plusSeconds(300))) return null
            val freshness = source.str("freshness") ?: return null
            if (freshness !in setOf("reported", "unverified")) return null
            val updated = source.str("source_updated_at")
            if (updated != null) OffsetDateTime.parse(updated)
            if ((updated == null) != (freshness == "unverified")) return null
            val rows = source.get("flights")?.takeIf { it.isJsonArray }?.asJsonArray ?: return null
            if (rows.size() > 250) return null
            val flights = rows.map { element ->
                if (!element.isJsonObject) return null
                val item = element.asJsonObject
                val number = item.str("flight_number") ?: return null
                val city = item.str("city") ?: return null
                val scheduled = item.str("scheduled_time") ?: return null
                if (number.length > 24 || city.length > 128 || scheduled.length > 40 ||
                    !(scheduled.matches(Regex("""\d{1,2}:\d{2}""")) ||
                      scheduled.matches(Regex("""\d{4}-\d{2}-\d{2}T\d{2}:\d{2}.*""")))) return null
                IranFlight(
                    flightNumber = number, airline = item.str("airline"),
                    city = city, scheduledTime = scheduled,
                    estimatedTime = item.str("estimated_time"),
                    actualTime = item.str("actual_time"),
                    status = item.str("status"),
                    terminal = item.str("terminal"), gate = item.str("gate"),
                )
            }
            IranFidsBoard(airport, direction, fetched, updated, freshness == "unverified", flights)
        }.getOrNull()

    private fun JsonObject.str(field: String): String? {
        val value: JsonElement = get(field) ?: return null
        if (value.isJsonNull || !value.isJsonPrimitive || !value.asJsonPrimitive.isString) return null
        return value.asString.trim().takeIf { it.isNotEmpty() && it.length <= 160 }
    }
}
