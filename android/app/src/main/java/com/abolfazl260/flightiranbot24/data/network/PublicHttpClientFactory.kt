package com.abolfazl260.flightiranbot24.data.network

import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient
import okhttp3.HttpUrl.Companion.toHttpUrl
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * Builds an unauthenticated public API client, without storing any secret.
 *
 * Production endpoints MUST use HTTPS. HTTP can only be explicitly enabled
 * for loopback MockWebServer in JVM integration tests. Neither redirects nor
 * automatic replays are enabled (mutating requests will require idempotency).
 */
internal object PublicHttpClientFactory {
    fun create(
        baseUrl: String,
        allowLoopbackHttpForTests: Boolean = false,
        callTimeoutMillis: Long = 12_000,
    ): RetrofitPublicJsonRepository {
        require(callTimeoutMillis in 1L..120_000L) { "Invalid call timeout" }
        val url = try {
            baseUrl.toHttpUrl()
        } catch (_: IllegalArgumentException) {
            throw IllegalArgumentException("Invalid API base URL")
        }
        val localTest = allowLoopbackHttpForTests &&
            url.scheme == "http" &&
            url.host in setOf("127.0.0.1", "localhost", "[::1]", "::1")
        require(url.scheme == "https" || localTest) {
            "HTTPS is required for a remote API"
        }
        require(
            url.username.isEmpty() && url.password.isEmpty() &&
                url.query == null && url.fragment == null &&
                url.encodedPath == "/"
        ) { "API base URL must be an origin with no credentials or query" }
        val client = OkHttpClient.Builder()
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(8, TimeUnit.SECONDS)
            .callTimeout(callTimeoutMillis, TimeUnit.MILLISECONDS)
            .followRedirects(false)
            .followSslRedirects(false)
            .retryOnConnectionFailure(false)
            .build()
        val retrofit = Retrofit.Builder()
            .baseUrl(url)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        return RetrofitPublicJsonRepository(retrofit.create(PublicJsonService::class.java))
    }
}
