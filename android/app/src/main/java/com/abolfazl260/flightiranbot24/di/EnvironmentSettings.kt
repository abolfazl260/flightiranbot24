package com.abolfazl260.flightiranbot24.di

import com.abolfazl260.flightiranbot24.BuildConfig
import com.abolfazl260.flightiranbot24.data.network.PublicHttpClientFactory
import com.abolfazl260.flightiranbot24.data.network.RetrofitPublicJsonRepository

/** Empty origin is an intentionally offline-only state, never a fallback. */
internal data class EnvironmentSettings(
    val name: String,
    val apiOrigin: String,
) {
    init {
        require(name in setOf("development", "staging", "production"))
        if (apiOrigin.isNotBlank()) {
            require(apiOrigin.endsWith("/")) { "API origin must end in /" }
            PublicHttpClientFactory.create(apiOrigin)
        }
    }

    val isProduction: Boolean get() = name == "production"
    val isConfigured: Boolean get() = apiOrigin.isNotBlank()

    fun publicApi(): RetrofitPublicJsonRepository? =
        apiOrigin.takeIf { it.isNotBlank() }?.let {
            PublicHttpClientFactory.create(it)
        }

    companion object {
        fun fromBuild() = EnvironmentSettings(
            BuildConfig.APP_ENVIRONMENT, BuildConfig.API_BASE_URL
        )
    }
}
