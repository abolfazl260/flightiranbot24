package com.abolfazl260.flightiranbot24.di

import com.abolfazl260.flightiranbot24.BuildConfig
import com.abolfazl260.flightiranbot24.data.network.PublicHttpClientFactory
import com.abolfazl260.flightiranbot24.data.network.RetrofitPublicJsonRepository

/** Exactly one application; an absent HTTPS endpoint fails closed for ticket prices. */
internal data class EnvironmentSettings(val apiOrigin: String) {
    init {
        if (apiOrigin.isNotBlank()) {
            require(apiOrigin.endsWith("/")) { "API origin must end in /" }
            PublicHttpClientFactory.create(apiOrigin)
        }
    }

    val isConfigured: Boolean get() = apiOrigin.isNotBlank()

    fun publicApi(): RetrofitPublicJsonRepository? =
        apiOrigin.takeIf { it.isNotBlank() }?.let { PublicHttpClientFactory.create(it) }

    companion object {
        fun fromBuild() = EnvironmentSettings(BuildConfig.API_BASE_URL)
    }
}
