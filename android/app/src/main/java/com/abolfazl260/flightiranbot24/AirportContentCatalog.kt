package com.abolfazl260.flightiranbot24

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.net.URI
import java.time.OffsetDateTime

/**
 * Content is keyed by IATA and section IDs, never by hard-coded "five features".
 * A new airport section using an existing block type needs only a JSON edit.
 * This is deliberately independent of the existing, currently disabled airport screen.
 */
internal data class AirportContentReference(val iata: String, val detailPath: String)
internal data class AirportContentIndex(val airports: List<AirportContentReference>)
internal data class AirportContentPage(
    val iata: String,
    val sections: List<AirportContentSection>,
)
internal data class AirportContentSection(
    val id: String,
    val title: String,
    val subtitle: String?,
    val icon: String,
    val order: Int,
    val reviewedAt: String,
    val sources: List<String>,
    val blocks: List<AirportContentBlock>,
)

internal sealed interface AirportContentBlock {
    data class Text(val content: String) : AirportContentBlock
    data class Bullets(val items: List<String>) : AirportContentBlock
    data class Link(val title: String, val url: String) : AirportContentBlock
    data class Image(val url: String, val alt: String, val caption: String?) : AirportContentBlock
    data class Video(
        val title: String,
        val url: String,
        val thumbnailUrl: String?,
        val credit: String?,
    ) : AirportContentBlock
    data class Map(
        val title: String,
        val latitude: Double,
        val longitude: Double,
        val externalUrl: String,
        val imageUrl: String?,
    ) : AirportContentBlock
    data class FlightBoard(val source: String, val direction: String) : AirportContentBlock
    data class Experience(
        val id: String,
        val text: String,
        val rating: Int,
        val visitDate: String,
    ) : AirportContentBlock
}

internal object AirportContentParser {
    private val codeRegex = Regex("[A-Z]{3}")
    private val idRegex = Regex("[a-z][a-z0-9-]{1,79}")

    fun parseIndex(json: String): AirportContentIndex {
        val root = JsonParser.parseString(json).asJsonObject
        require(root.get("schema_version")?.asInt == 1) { "Unsupported airport index version" }
        val rows = root.getAsJsonArray("airports") ?: error("Missing airport list")
        require(rows.size() <= 1000) { "Airport index too large" }
        val seen = mutableSetOf<String>()
        val entries = rows.mapNotNull { item ->
            val entry = item.asJsonObject
            val code = entry.text("iata")
            val path = entry.text("detail_path")
            require(codeRegex.matches(code)) { "Invalid IATA code" }
            require(path == "details/" + code + ".v1.json") { "Invalid airport detail path" }
            require(seen.add(code)) { "Duplicate airport entry" }
            if (!entry.get("enabled").asBoolean) null else AirportContentReference(code, path)
        }
        return AirportContentIndex(entries.sortedBy { it.iata })
    }

    fun parseDetail(json: String, iata: String): AirportContentPage {
        require(codeRegex.matches(iata)) { "Invalid requested airport code" }
        val root = JsonParser.parseString(json).asJsonObject
        require(root.get("schema_version")?.asInt == 1) { "Unsupported airport detail version" }
        require(root.text("iata") == iata) { "Airport content identity mismatch" }
        val rows = root.getAsJsonArray("sections") ?: error("Missing sections")
        require(rows.size() <= 100) { "Too many airport sections" }
        val seen = mutableSetOf<String>()
        val sections = rows.mapNotNull { item ->
            val entry = item.asJsonObject
            val id = entry.text("id")
            require(idRegex.matches(id) && seen.add(id)) { "Duplicate or invalid section ID" }
            if (entry.text("status") != "published") return@mapNotNull null
            val reviewed = entry.text("reviewed_at")
            OffsetDateTime.parse(reviewed)
            val sources = entry.getAsJsonArray("source_urls")?.map { safeHttps(it.asString) }
                ?: emptyList()
            val allBlocks = entry.getAsJsonArray("blocks") ?: error("Missing section blocks")
            require(allBlocks.size() <= 200) { "Too many section blocks" }
            val blocks = allBlocks.mapNotNull { parseBlock(it) }
            // Newer unknown block types must not produce blank cards.
            if (blocks.isEmpty()) return@mapNotNull null
            require(
                sources.isNotEmpty() || blocks.all { it is AirportContentBlock.Experience }
            ) { "Factual section missing official source" }
            AirportContentSection(
                id = id,
                title = entry.text("title_fa"),
                subtitle = entry.optionalText("subtitle_fa"),
                icon = entry.text("icon"),
                order = entry.get("order").asInt,
                reviewedAt = reviewed,
                sources = sources,
                blocks = blocks,
            )
        }
        return AirportContentPage(iata, sections.sortedWith(compareBy({ it.order }, { it.id })))
    }

    private fun parseBlock(json: JsonElement): AirportContentBlock? {
        if (!json.isJsonObject) return null
        val block = json.asJsonObject
        return when (block.get("type")?.asString) {
            "text" -> AirportContentBlock.Text(block.text("text_fa"))
            "bullets" -> AirportContentBlock.Bullets(
                block.getAsJsonArray("items_fa").map { it.asString }.also {
                    require(it.isNotEmpty() && it.all(String::isNotBlank))
                }
            )
            "link" -> AirportContentBlock.Link(block.text("title_fa"), safeHttps(block.text("url")))
            "image" -> AirportContentBlock.Image(
                safeHttps(block.text("url")),
                block.text("alt_fa"),
                block.optionalText("caption_fa"),
            )
            "video" -> AirportContentBlock.Video(
                block.text("title_fa"),
                safeHttps(block.text("url")),
                block.optionalText("thumbnail_url")?.let(::safeHttps),
                block.optionalText("attribution_fa"),
            )
            "map" -> {
                val latitude = block.get("latitude").asDouble
                val longitude = block.get("longitude").asDouble
                require(latitude in -90.0..90.0 && longitude in -180.0..180.0)
                AirportContentBlock.Map(
                    block.text("title_fa"), latitude, longitude,
                    safeHttps(block.text("external_url")),
                    block.optionalText("image_url")?.let(::safeHttps),
                )
            }
            "flight_board" -> {
                val source = block.text("data_source")
                val direction = block.text("direction")
                require(source == "iran_fids" && direction in setOf("both", "arrivals", "departures"))
                AirportContentBlock.FlightBoard(source, direction)
            }
            "experience" -> {
                require(block.get("approved").asBoolean) { "Unapproved user experience" }
                val rating = block.get("rating").asInt
                require(rating in 1..5)
                AirportContentBlock.Experience(
                    block.text("id"), block.text("text_fa"), rating, block.text("visit_date")
                )
            }
            else -> null // Forward-compatible, non-executable presentation fallback.
        }
    }

    private fun JsonObject.text(key: String): String =
        optionalText(key) ?: throw IllegalArgumentException("Missing " + key)

    private fun JsonObject.optionalText(key: String): String? =
        get(key)?.takeUnless { it.isJsonNull }?.asString?.trim()?.takeIf(String::isNotEmpty)

    private fun safeHttps(value: String): String {
        val uri = URI(value)
        require(
            uri.scheme == "https" && !uri.host.isNullOrBlank() &&
                uri.rawUserInfo == null && uri.port != 0
        ) { "Public airport links must be HTTPS" }
        return value
    }
}
