package com.abolfazl260.flightiranbot24

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.net.URI
import java.time.Instant
import java.time.LocalDate
import java.util.Locale

internal data class AirlineReference(
    val id: String, val path: String, val name: String, val nameEn: String,
    val country: String, val countryName: String, val searchNames: List<String>,
    val codes: List<String>, val website: String, val reviewedAt: String,
)
internal data class AirlinePolicyScope(
    val note: String, val route: String?, val fare: String?, val cabin: String?,
    val operatingCarrier: String?, val seller: String, val journeyType: String,
)
internal data class AirlineSection(
    val id: String, val title: String, val order: Int, val reviewedAt: String,
    val sources: List<String>, val scope: AirlinePolicyScope?, val blocks: List<AirlineBlock>,
    val reviewOverdue: Boolean = false,
)
internal data class AirlinePage(
    val id: String, val reviewedAt: String, val sections: List<AirlineSection>,
    val ratingCount: Int, val criterionCounts: Map<String, Int>,
) {
    // No product-approved sample threshold yet: counts only, never synthetic stars.
    val average: Double? get() = null
}
internal sealed interface AirlineBlock {
    data class Content(val block: AirportContentBlock) : AirlineBlock
    data class Fleet(
        val model: String, val manufacturer: String, val count: Int?, val observedAt: String,
        val status: String, val relationship: String, val configuration: String?,
        val sources: List<String>,
    ) : AirlineBlock
    data class Airport(val iata: String, val title: String) : AirlineBlock
    data class Route(
        val origin: String, val destination: String, val serviceType: String,
        val operatingCarrier: String?, val status: String, val observedAt: String,
        val note: String, val sources: List<String>,
    ) : AirlineBlock
    data class Media(val title: String, val url: String, val attribution: String) : AirlineBlock
}

internal object AirlineContentParser {
    private val idPattern = Regex("[a-z][a-z0-9-]{1,79}")
    val criteria = linkedMapOf(
        "overall" to "رضایت کلی", "crew" to "رفتار خدمه", "seat" to "راحتی صندلی",
        "cleanliness" to "نظافت", "catering" to "پذیرایی", "checkin" to "پذیرش و سوارشدن",
        "baggage" to "مدیریت بار", "value" to "ارزش در برابر هزینه",
    )

    fun index(json: String, now: Instant = Instant.now()): List<AirlineReference> {
        val root = JsonParser.parseString(json).asJsonObject
        require(root.get("schema_version").asInt == 1)
        val seen = mutableSetOf<String>()
        val rows = root.getAsJsonArray("airlines")
        require(rows.size() <= 1000)
        return rows.mapNotNull {
            val row = it.asJsonObject
            val id = row.text("airline_id")
            require(idPattern.matches(id) && seen.add(id))
            val path = row.text("detail_path")
            require(path == "details/$id.v1.json")
            if (!published(row.getAsJsonObject("metadata"), now)) return@mapNotNull null
            val identity = row.getAsJsonObject("identity")
            val codes = identity.getAsJsonArray("codes").mapNotNull { element ->
                val code = element.asJsonObject
                val value = code.text("value")
                require(when (code.text("system")) {
                    "iata" -> value.matches(Regex("[A-Z0-9]{2}"))
                    "icao" -> value.matches(Regex("[A-Z]{3}"))
                    else -> false
                })
                if (withinPeriod(code, "valid_from", "valid_to", now)) value else null
            }
            val country = identity.text("country")
            require(country.matches(Regex("[A-Z]{2}")))
            AirlineReference(
                id, path, identity.text("name_fa"), identity.text("name_en"), country,
                identity.text("country_fa"), listOf(identity.text("legal_name")) +
                    identity.getAsJsonArray("aliases").map { a -> a.asString } +
                    identity.getAsJsonArray("former_names").map { a -> a.asString },
                codes, https(identity.text("website")), row.getAsJsonObject("metadata").text("verified_at"),
            )
        }
    }

    fun detail(json: String, id: String, now: Instant = Instant.now()): AirlinePage? {
        require(idPattern.matches(id))
        val root = JsonParser.parseString(json).asJsonObject
        require(root.get("schema_version").asInt == 1 && root.text("airline_id") == id)
        val metadata = root.getAsJsonObject("metadata")
        if (!published(metadata, now)) return null
        val seen = mutableSetOf<String>()
        val rows = root.getAsJsonArray("sections")
        require(rows.size() <= 100)
        val sections = rows.mapNotNull {
            val row = it.asJsonObject
            val sectionId = row.text("id")
            require(idPattern.matches(sectionId) && seen.add(sectionId))
            val meta = row.getAsJsonObject("metadata")
            if (!published(meta, now)) return@mapNotNull null
            val scope = row.get("scope")?.takeUnless { s -> s.isJsonNull }?.asJsonObject
            require(row.text("kind") != "policy" || scope != null)
            val blocks = row.getAsJsonArray("blocks")
            require(blocks.size() <= 200)
            val rendered = blocks.mapNotNull { b ->
                require(b.asJsonObject.text("type") != "route_snapshot" || row.text("kind") == "network")
                block(b.asJsonObject, now)
            }
            if (rendered.isEmpty()) return@mapNotNull null
            AirlineSection(sectionId, row.text("title_fa"), row.get("order").asInt,
                meta.text("verified_at"), sources(meta), scope?.let { policy ->
                    AirlinePolicyScope(policy.text("note_fa"), policy.optional("route"),
                        policy.optional("fare_brand"), policy.optional("cabin_class"),
                        policy.optional("operating_carrier"), policy.text("seller"),
                        policy.text("journey_type"))
                }, rendered, Instant.parse(meta.text("verified_at")) < now.minusSeconds(30L * 86400))
        }.sortedWith(compareBy({ it.order }, { it.id }))
        val reviewIds = mutableSetOf<String>()
        val counts = criteria.keys.associateWith { 0 }.toMutableMap()
        val reviews = root.getAsJsonArray("published_reviews")
        require(reviews.size() <= 1000)
        var valid = 0
        reviews.forEach {
            val review = it.asJsonObject
            // Invalid/unapproved reviews never contribute to visible counts.
            if (review.text("airline_id") != id ||
                review.text("consent_status") != "granted" ||
                review.text("moderation_status") != "approved" ||
                !review.get("verified_origin").asBoolean ||
                !review.get("privacy_reviewed").asBoolean ||
                review.get("conflict_of_interest").asBoolean
            ) return@forEach
            require(Instant.parse(review.text("publication_timestamp")) <= now)
            review.optional("visit_date")?.let(LocalDate::parse)
            require(reviewIds.add(review.text("review_id")))
            val ratings = review.getAsJsonObject("ratings")
            require(ratings.size() > 0)
            ratings.entrySet().forEach { (criterion, value) ->
                require(criterion in criteria && value.isJsonPrimitive && value.asJsonPrimitive.isNumber)
                require(value.asDouble in 1.0..5.0 && value.asDouble == value.asInt.toDouble())
                counts[criterion] = counts.getValue(criterion) + 1
            }
            valid++
        }
        return AirlinePage(id, metadata.text("verified_at"), sections, valid, counts)
    }

    private fun block(row: JsonObject, now: Instant): AirlineBlock? = when (row.text("type")) {
        "text" -> AirlineBlock.Content(AirportContentBlock.Text(row.text("text_fa")))
        "bullets" -> AirlineBlock.Content(AirportContentBlock.Bullets(
            row.getAsJsonArray("items_fa").map { it.asString }.also {
                require(it.isNotEmpty() && it.size <= 50 && it.all(String::isNotBlank))
            }))
        "link" -> AirlineBlock.Content(AirportContentBlock.Link(row.text("title_fa"), https(row.text("url"))))
        "fleet_snapshot" -> {
            val meta = row.getAsJsonObject("metadata")
            if (!published(meta, now)) null else {
                val observed = row.text("observed_at")
                require(Instant.parse(observed) <= now)
                val value = row.get("count")?.takeUnless { it.isJsonNull }
                val count = value?.let {
                    require(it.asJsonPrimitive.isNumber && it.asDouble >= 0 &&
                        it.asDouble == it.asInt.toDouble())
                    it.asInt
                }
                val status = row.text("status")
                val relationship = row.text("relationship")
                require(status in setOf("active", "stored", "leased-in", "leased-out", "retired", "unknown"))
                require(relationship in setOf("owned", "operated", "leased", "unknown"))
                AirlineBlock.Fleet(row.text("model"), row.text("manufacturer"), count, observed,
                    status, relationship, row.optional("configuration_fa"), sources(meta))
            }
        }
        "airport_link" -> {
            val code = row.text("iata")
            require(code.matches(Regex("[A-Z]{3}")))
            AirlineBlock.Airport(code, row.text("title_fa"))
        }
        "route_snapshot" -> {
            val meta = row.getAsJsonObject("metadata")
            if (!published(meta, now)) null else {
                val origin = row.text("origin")
                val destination = row.text("destination")
                require(origin.matches(Regex("[A-Z]{3}")) && destination.matches(Regex("[A-Z]{3}")) && origin != destination)
                val service = row.text("service_type")
                val status = row.text("status")
                val carrier = row.optional("operating_carrier")
                val observed = row.text("observed_at")
                require(service in setOf("non_stop", "connecting", "unknown"))
                require(status in setOf("listed", "announced", "seasonal", "suspended", "unknown"))
                require(carrier == null || idPattern.matches(carrier))
                require(Instant.parse(observed) <= now)
                AirlineBlock.Route(origin, destination, service, carrier, status, observed,
                    row.text("note_fa"), sources(meta))
            }
        }
        "image", "video" -> {
            require(row.get("rights_verified").asBoolean)
            row.text("license")
            https(row.text("source_url"))
            AirlineBlock.Media(row.text("title_fa"), https(row.text("url")), row.text("attribution_fa"))
        }
        else -> null
    }

    private fun published(meta: JsonObject, now: Instant): Boolean {
        if (meta.text("status") != "published" || meta.get("stale").asBoolean) return false
        require(meta.text("confidence") in setOf("official", "secondary"))
        require(Instant.parse(meta.text("verified_at")) <= now)
        require(sources(meta).isNotEmpty())
        return withinPeriod(meta, "effective_from", "effective_to", now)
    }

    private fun withinPeriod(row: JsonObject, from: String, to: String, now: Instant): Boolean {
        val start = row.optional(from)?.let(Instant::parse)
        val end = row.optional(to)?.let(Instant::parse)
        require(start == null || end == null || start <= end)
        return (start == null || now >= start) && (end == null || now <= end)
    }

    private fun sources(meta: JsonObject) = meta.getAsJsonArray("source_urls").map { https(it.asString) }
    private fun JsonObject.text(key: String): String = optional(key) ?: error("Missing $key")
    private fun JsonObject.optional(key: String): String? =
        get(key)?.takeUnless { it.isJsonNull }?.asString?.takeIf(String::isNotBlank)

    fun https(value: String): String {
        val uri = URI(value)
        require(uri.scheme == "https" && !uri.host.isNullOrBlank() &&
            uri.rawUserInfo == null && uri.port != 0)
        return value
    }
}

internal fun filterAirlines(rows: List<AirlineReference>, query: String, region: String): List<AirlineReference> {
    fun normalize(value: String) = value.lowercase(Locale.ROOT).replace('ي', 'ی').replace('ك', 'ک')
        .replace("\u200c", "").replace(" ", "").trim()
    val needle = normalize(query)
    return rows.filter { row ->
        (region == "all" || (row.country == "IR") == (region == "iran")) &&
            (listOf(row.name, row.nameEn) + row.searchNames + row.codes).any { needle in normalize(it) }
    }.sortedBy { it.name }
}
