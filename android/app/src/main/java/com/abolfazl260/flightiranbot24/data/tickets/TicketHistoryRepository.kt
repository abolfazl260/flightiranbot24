package com.abolfazl260.flightiranbot24.data.tickets

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject
import java.net.URLEncoder
import java.time.Instant
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneOffset

internal data class HistoryPoint(val day: LocalDate, val price: Long, val samples: Int, val observed: Instant)
internal data class TicketHistory(val origin: String, val destination: String, val asOf: LocalDate,
    val points: List<HistoryPoint>, val observed: Instant?, val stale: Boolean) {
    val minimum get() = points.minOfOrNull { it.price }
    val maximum get() = points.maxOfOrNull { it.price }
    val samples get() = points.sumOf { it.samples }
    val start get() = asOf.minusDays(20)
    val segments get() = points.zipWithNext().filter { (a,b) -> a.day.plusDays(1) == b.day }
}
internal data class HistoryRoutes(val routes: List<Pair<String,String>>, val next: Int?)
internal class TicketHistoryRepository(private val api: PublicJsonRepository<JsonObject>?) {
    suspend fun load(origin: String, destination: String): TicketHistory {
        fun encode(s: String) = URLEncoder.encode(s,"UTF-8")
        val result = api?.fetch("api/v1/tickets/history?origin=${encode(origin)}&destination=${encode(destination)}")
        val json = (result as? NetworkResult.Success)?.value ?: error("History unavailable")
        val value = parse(json) ?: error("Invalid history")
        require(value.origin == origin && value.destination == destination)
        return value
    }
    suspend fun routes(offset: Int = 0): HistoryRoutes {
        require(offset in 0..10000)
        val result = api?.fetch("api/v1/tickets/history/routes?offset=$offset")
        val json = (result as? NetworkResult.Success)?.value ?: error("Routes unavailable")
        val routes = json.getAsJsonArray("routes"); require(routes.size() <= 100)
        val rows = routes.map { it.asJsonObject.let { r -> r.get("origin").asString to r.get("destination").asString } }
        require(rows.all { it.first.length in 1..128 && it.second.length in 1..128 })
        val next = json.get("next_offset")?.takeUnless { it.isJsonNull }?.asInt
        require(next == null || next in (offset+1)..10000)
        return HistoryRoutes(rows,next)
    }
    fun parse(raw: JsonObject, now: Instant = Instant.now()): TicketHistory? = runCatching {
        require(raw.get("currency").asString == "TOMAN" && raw.get("metric").asString == "daily_minimum" && raw.get("days").asInt == 21)
        val origin = raw.get("origin").asString; val destination = raw.get("destination").asString
        require(origin.length in 1..128 && destination.length in 1..128)
        val end = LocalDate.parse(raw.get("as_of").asString)
        require(!end.isAfter(now.atOffset(ZoneOffset.UTC).toLocalDate()))
        val values = raw.getAsJsonArray("points"); require(values.size() <= 21)
        fun integer(row: JsonObject, key: String, max: Double): Long {
            val p = row.get(key); require(p.isJsonPrimitive && p.asJsonPrimitive.isNumber)
            val n = p.asDouble; require(n.isFinite() && n > 0 && n <= max && n % 1.0 == 0.0)
            return n.toLong()
        }
        val points = values.map { p ->
            val row = p.asJsonObject; val day = LocalDate.parse(row.get("day").asString)
            val observed = OffsetDateTime.parse(row.get("last_observed_at").asString).toInstant()
            require(day >= end.minusDays(20) && day <= end && observed <= now.plusSeconds(300))
            require(observed.atOffset(ZoneOffset.UTC).toLocalDate() == day)
            HistoryPoint(day,integer(row,"price_toman",1e12),integer(row,"sample_count",100000.0).toInt(),observed)
        }
        require(points.zipWithNext().all { (a,b) -> a.day < b.day })
        val observed = points.maxOfOrNull { it.observed }
        val published = raw.get("observed_at")?.takeUnless { it.isJsonNull }?.asString?.let { OffsetDateTime.parse(it).toInstant() }
        require(published == observed)
        TicketHistory(origin,destination,end,points,observed,
            raw.get("stale")?.asBoolean != false || observed == null || observed < now.minusSeconds(10800))
    }.getOrNull()
}
