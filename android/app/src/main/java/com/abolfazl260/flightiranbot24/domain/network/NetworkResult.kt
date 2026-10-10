package com.abolfazl260.flightiranbot24.domain.network

/**
 * Transport-level result. API-001 will introduce typed business DTOs and
 * stable server errors; this layer never invents a production API contract.
 */
internal sealed interface NetworkResult<out T> {
    data class Success<T>(val value: T) : NetworkResult<T>
    data class HttpFailure(val statusCode: Int) : NetworkResult<Nothing>
    data object InvalidEndpoint : NetworkResult<Nothing>
    data object InvalidResponse : NetworkResult<Nothing>
    data object Timeout : NetworkResult<Nothing>
    data object ConnectionFailure : NetworkResult<Nothing>
}

internal interface PublicJsonRepository<T> {
    suspend fun fetch(relativePath: String): NetworkResult<T>
}
