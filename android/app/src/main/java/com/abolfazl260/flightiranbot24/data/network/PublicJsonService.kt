package com.abolfazl260.flightiranbot24.data.network

import com.google.gson.JsonObject
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Url

/**
 * Endpoint is supplied by a separately tested, versioned server API.
 * No Telegram session, provider URL, bot token or fake endpoint is embedded.
 */
internal interface PublicJsonService {
    @GET
    suspend fun getJson(@Url relativePath: String): Response<JsonObject>
}
