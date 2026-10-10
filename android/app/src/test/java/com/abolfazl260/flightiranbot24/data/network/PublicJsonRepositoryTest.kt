package com.abolfazl260.flightiranbot24.data.network

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PublicJsonRepositoryTest {
    @Test
    fun productionApiRejectsHttpCredentialsAndPaths() {
        val unsecured = listOf(
            "http://example.com/", "https://user:secret@example.com/",
            "https://example.com/api/", "https://example.com/?token=1",
            "https://example.com/#fragment",
        )
        for (url in unsecured) {
            try {
                PublicHttpClientFactory.create(url)
                throw AssertionError("Accepted unsafe API base URL: $url")
            } catch (_: IllegalArgumentException) {
                // No exception data including an embedded credential is logged.
            }
        }
        val secure = PublicHttpClientFactory.create("https://api.example.com/")
        assertTrue(secure is RetrofitPublicJsonRepository)
    }

    @Test
    fun parsesVersionedPublicResponseAndPreservesServerStatus() = runBlocking {
        MockWebServer().use { server ->
            server.start()
            server.enqueue(
                MockResponse()
                    .setResponseCode(200)
                    .setHeader("Content-Type", "application/json")
                    .setBody("{\"status\":\"ready\",\"count\":3}")
            )
            server.enqueue(
                MockResponse().setResponseCode(503).setBody("{\"error\":\"unavailable\"}")
            )
            val client = PublicHttpClientFactory.create(
                server.url("/").toString(), allowLoopbackHttpForTests = true
            )
            val ok = client.fetch("api/v1/public-health")
            assertTrue(ok is NetworkResult.Success)
            assertEquals(
                "ready",
                (ok as NetworkResult.Success).value.get("status").asString,
            )
            assertEquals(3, ok.value.get("count").asInt)
            assertEquals("GET /api/v1/public-health HTTP/1.1", server.takeRequest().requestLine)
            assertEquals(
                NetworkResult.HttpFailure(503),
                client.fetch("api/v1/public-health"),
            )
        }
    }

    @Test
    fun malformedDataAndUnsafeRedirectsCannotMasqueradeAsSuccess() = runBlocking {
        MockWebServer().use { server ->
            server.start()
            server.enqueue(MockResponse().setBody("this is not JSON"))
            server.enqueue(
                MockResponse()
                    .setResponseCode(302)
                    .setHeader("Location", "https://attacker.invalid/collect")
            )
            val client = PublicHttpClientFactory.create(
                server.url("/").toString(), allowLoopbackHttpForTests = true
            )
            assertEquals(NetworkResult.InvalidResponse, client.fetch("api/v1/countries"))
            assertEquals(NetworkResult.HttpFailure(302), client.fetch("api/v1/countries"))
            assertEquals(2, server.requestCount)
        }
    }

    @Test
    fun rejectsAbsoluteUrlsTraversalQueriesAndMalformedEndpointsBeforeNetwork() = runBlocking {
        MockWebServer().use { server ->
            server.start()
            val client = PublicHttpClientFactory.create(
                server.url("/").toString(), allowLoopbackHttpForTests = true
            )
            for (bad in listOf(
                "", "../api/v1/countries", "api/v2/countries", "api/v1/../secrets",
                "https://example.com/", "//other-host/", "api/v1/countries?token=test",
                "api/v1/%2e%2e/secrets", "api/v1/name#fragment", "api/v1/countries/",
            )) {
                assertEquals(bad, NetworkResult.InvalidEndpoint, client.fetch(bad))
            }
            assertEquals(0, server.requestCount)
        }
    }

    @Test
    fun timeoutReturnsRetryableTypedFailureWithoutLeakingTransportText() = runBlocking {
        MockWebServer().use { server ->
            server.start()
            server.enqueue(
                MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE)
            )
            val client = PublicHttpClientFactory.create(
                server.url("/").toString(),
                allowLoopbackHttpForTests = true,
                callTimeoutMillis = 160,
            )
            assertEquals(NetworkResult.Timeout, client.fetch("api/v1/airports"))
        }
    }

    @Test
    fun connectionFailuresRemainSeparateFromBadResponses() = runBlocking {
        val server = MockWebServer()
        server.start()
        val base = server.url("/").toString()
        server.shutdown()
        val client = PublicHttpClientFactory.create(
            base, allowLoopbackHttpForTests = true, callTimeoutMillis = 900
        )
        assertEquals(NetworkResult.ConnectionFailure, client.fetch("api/v1/airports"))
    }

    @Test
    fun refusesImplicitHttpInRealAppEvenWhenServerLooksLocal() {
        val client = PublicHttpClientFactory.create(
            "https://example.org/", allowLoopbackHttpForTests = false
        )
        assertFalse(client.toString().isEmpty())
        try {
            PublicHttpClientFactory.create("http://127.0.0.1:1234/")
            throw AssertionError("Should require explicit HTTP test mode")
        } catch (_: IllegalArgumentException) {
            // Allowed only when an explicit localhost test opt-in is passed.
        }
    }
}
