package com.abolfazl260.flightiranbot24

import android.content.Context
import com.google.gson.JsonParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.URI
import java.util.concurrent.TimeUnit

/** The Android directory reads the exact shared GitHub catalog, never a parallel list. */
internal data class TravelWebsiteCategory(val id: String, val title: String, val order: Int)

internal data class TravelWebsite(
    val id: String,
    val title: String,
    val description: String,
    val categoryId: String,
    val url: String,
    val imagePath: String,
    val order: Int,
)

internal data class TravelWebsiteCatalog(
    val categories: List<TravelWebsiteCategory>,
    val websites: List<TravelWebsite>,
)

internal object TravelWebsiteCatalogParser {
    fun parse(json: String): TravelWebsiteCatalog {
        val root = JsonParser.parseString(json).asJsonObject
        require(root.get("schema_version")?.asInt == 1) { "Unsupported catalog schema" }

        val categories = root.getAsJsonArray("categories").map { element ->
            val obj = element.asJsonObject
            TravelWebsiteCategory(
                id = obj.get("id").asString,
                title = obj.get("name_fa").asString,
                order = obj.get("order").asInt,
            )
        }.sortedWith(compareBy({ it.order }, { it.id }))
        require(categories.isNotEmpty() && categories.map { it.id }.distinct().size == categories.size) {
            "Invalid categories"
        }
        val categoryIds = categories.map { it.id }.toSet()
        val websites = root.getAsJsonArray("websites").mapNotNull { element ->
            val obj = element.asJsonObject
            if (!obj.get("enabled").asBoolean) return@mapNotNull null
            val url = obj.get("url").asString
            val uri = URI(url)
            require(uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.rawUserInfo == null) {
                "Catalog website URL must use HTTPS"
            }
            val categoryId = obj.get("category_id").asString
            require(categoryId in categoryIds) { "Unknown catalog category" }
            val imagePath = obj.get("image").asString
            require(Regex("^images/[a-z0-9][a-z0-9._-]*\\.webp$").matches(imagePath)) {
                "Invalid catalog image path"
            }
            TravelWebsite(
                id = obj.get("id").asString,
                title = obj.get("name_fa").asString,
                description = obj.get("description_fa").asString,
                categoryId = categoryId,
                url = url,
                imagePath = imagePath,
                order = obj.get("order").asInt,
            )
        }.sortedWith(compareBy({ it.order }, { it.id }))
        require(websites.isNotEmpty() && websites.map { it.id }.distinct().size == websites.size) {
            "Invalid websites"
        }
        return TravelWebsiteCatalog(categories, websites)
    }
}

internal class TravelWebsiteCatalogRepository(private val context: Context) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .callTimeout(10, TimeUnit.SECONDS)
        .build()

    suspend fun bundled(): TravelWebsiteCatalog = withContext(Dispatchers.IO) {
        val json = context.assets.open("catalog.v1.json").bufferedReader(Charsets.UTF_8).use { it.readText() }
        TravelWebsiteCatalogParser.parse(json)
    }

    /** Fetch on opening/refresh; no persistent copy or user data is stored. */
    suspend fun latest(): TravelWebsiteCatalog = withContext(Dispatchers.IO) {
        val request = Request.Builder().url(CATALOG_URL).header("Accept", "application/json").build()
        client.newCall(request).execute().use { response ->
            check(response.isSuccessful) { "Catalog HTTP ${response.code}" }
            val body = requireNotNull(response.body) { "Empty catalog response" }
            require(body.contentLength() in -1L..MAX_BYTES.toLong()) { "Catalog too large" }
            val bytes = body.byteStream().use { stream -> stream.readNBytes(MAX_BYTES + 1) }
            require(bytes.size <= MAX_BYTES) { "Catalog too large" }
            TravelWebsiteCatalogParser.parse(bytes.toString(Charsets.UTF_8))
        }
    }

    private companion object {
        const val MAX_BYTES = 256_000
        const val CATALOG_URL =
            "https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/travel-websites/catalog.v1.json"
    }
}
