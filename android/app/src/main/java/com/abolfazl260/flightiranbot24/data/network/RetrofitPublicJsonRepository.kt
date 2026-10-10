package com.abolfazl260.flightiranbot24.data.network

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject
import com.google.gson.JsonParseException
import java.io.IOException
import java.net.SocketTimeoutException
import kotlinx.coroutines.CancellationException

internal class RetrofitPublicJsonRepository(
    private val service: PublicJsonService,
) : PublicJsonRepository<JsonObject> {
    /**
     * Path must stay within our own versioned API. Do not allow absolute URLs,
     * traversal, query strings, user-info, or provider endpoints through @Url.
     */
    override suspend fun fetch(relativePath: String): NetworkResult<JsonObject> {
        if (!API_PATH.matches(relativePath)) {
            return NetworkResult.InvalidEndpoint
        }
        return try {
            val response = service.getJson(relativePath)
            if (!response.isSuccessful) {
                NetworkResult.HttpFailure(response.code())
            } else {
                val payload = response.body()
                if (payload == null) NetworkResult.InvalidResponse
                else NetworkResult.Success(payload)
            }
        } catch (cancel: CancellationException) {
            throw cancel
        } catch (_: SocketTimeoutException) {
            NetworkResult.Timeout
        } catch (_: JsonParseException) {
            NetworkResult.InvalidResponse
        } catch (_: IOException) {
            NetworkResult.ConnectionFailure
        }
    }

    private companion object {
        // A literal /api/v1 prefix provides a stable mount point while API-001
        // defines the actual endpoints. No app screen calls this yet.
        val API_PATH = Regex("""api/v1/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+""")
    }
}
