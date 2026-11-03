package com.abolfazl260.flightiranbot24

import android.content.Context
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request

/** JSON is public and can be refreshed after release, without shipping new Android binaries. */
internal data class AirportContentLoad<T>(val value: T, val usedBundledFallback: Boolean)

internal class AirportContentRepository(private val context: Context) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .callTimeout(10, TimeUnit.SECONDS)
        .followRedirects(false)
        .build()

    /**
     * Index is small; airport-specific data is not downloaded until that airport is selected.
     * No persistent cache, cookies, account data, provider credentials or HTML execution.
     */
    suspend fun index(): AirportContentLoad<AirportContentIndex> = withContext(Dispatchers.IO) {
        fetchWithBundledFallback(
            "airport-index.v1.json", INDEX_MAX_BYTES, AirportContentParser::parseIndex
        )
    }

    suspend fun detail(reference: AirportContentReference): AirportContentLoad<AirportContentPage> =
        withContext(Dispatchers.IO) {
            require(reference.iata.matches(Regex("[A-Z]{3}")))
            require(reference.detailPath == "details/" + reference.iata + ".v1.json")
            fetchWithBundledFallback(reference.detailPath, DETAIL_MAX_BYTES) {
                AirportContentParser.parseDetail(it, reference.iata)
            }
        }

    private fun <T> fetchWithBundledFallback(
        path: String,
        maxBytes: Int,
        parser: (String) -> T,
    ): AirportContentLoad<T> {
        try {
            val request = Request.Builder()
                .url(BASE_URL + path)
                .header("Accept", "application/json")
                .build()
            client.newCall(request).execute().use { response ->
                check(response.isSuccessful) { "Airport catalog HTTP " + response.code }
                val body = requireNotNull(response.body)
                require(body.contentLength() in -1L..maxBytes.toLong())
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                body.byteStream().use { stream ->
                    while (true) {
                        val count = stream.read(buffer)
                        if (count < 0) break
                        require(output.size() + count <= maxBytes) { "Airport catalog too large" }
                        output.write(buffer, 0, count)
                    }
                }
                return AirportContentLoad(parser(output.toByteArray().toString(Charsets.UTF_8)), false)
            }
        } catch (cancel: CancellationException) {
            throw cancel
        } catch (_: Exception) {
            val bytes = context.assets.open(path).use { it.readBytes() }
            require(bytes.size <= maxBytes) { "Bundled airport catalog too large" }
            return AirportContentLoad(parser(bytes.toString(Charsets.UTF_8)), true)
        }
    }

    private companion object {
        private const val INDEX_MAX_BYTES = 64_000
        private const val DETAIL_MAX_BYTES = 512_000
        private const val BASE_URL =
            "https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/airports/"
    }
}
