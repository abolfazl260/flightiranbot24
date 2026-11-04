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

internal class AirlineContentRepository(
    private val context: Context,
    private val baseUrl: String = BASE_URL,
    private val client: OkHttpClient = defaultClient(),
) {
    /** Production transport is bounded and never follows redirects. */
    private companion object {
        const val INDEX_MAX_BYTES = 64_000
        const val DETAIL_MAX_BYTES = 512_000
        const val BASE_URL =
            "https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/airlines/"
        fun defaultClient() = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .callTimeout(10, TimeUnit.SECONDS)
        .followRedirects(false)
        .build()
    }

    /**
     * Index is small; airline-specific data is not downloaded until that airline is selected.
     * No persistent cache, cookies, account data, provider credentials or HTML execution.
     */
    suspend fun index(): AirportContentLoad<List<AirlineReference>> = withContext(Dispatchers.IO) {
        fetchWithBundledFallback(
            "airline-index.v1.json", INDEX_MAX_BYTES, { AirlineContentParser.index(it) }
        )
    }

    suspend fun detail(reference: AirlineReference): AirportContentLoad<AirlinePage?> =
        withContext(Dispatchers.IO) {
            require(reference.id.matches(Regex("[a-z][a-z0-9-]{1,79}")))
            require(reference.path == "details/" + reference.id + ".v1.json")
            fetchWithBundledFallback(reference.path, DETAIL_MAX_BYTES) {
                AirlineContentParser.detail(it, reference.id)
            }
        }

    private fun <T> fetchWithBundledFallback(
        path: String,
        maxBytes: Int,
        parser: (String) -> T,
    ): AirportContentLoad<T> {
        try {
            val request = Request.Builder()
                .url(baseUrl + path)
                .header("Accept", "application/json")
                .build()
            client.newCall(request).execute().use { response ->
                check(response.isSuccessful) { "Airline catalog HTTP " + response.code }
                val body = requireNotNull(response.body)
                require(body.contentLength() in -1L..maxBytes.toLong())
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                body.byteStream().use { stream ->
                    while (true) {
                        val count = stream.read(buffer)
                        if (count < 0) break
                        require(output.size() + count <= maxBytes) { "Airline catalog too large" }
                        output.write(buffer, 0, count)
                    }
                }
                return AirportContentLoad(parser(output.toByteArray().toString(Charsets.UTF_8)), false)
            }
        } catch (cancel: CancellationException) {
            throw cancel
        } catch (_: Exception) {
            val bytes = context.assets.open(path).use { it.readBytes() }
            require(bytes.size <= maxBytes) { "Bundled airline catalog too large" }
            return AirportContentLoad(parser(bytes.toString(Charsets.UTF_8)), true)
        }
    }

}
