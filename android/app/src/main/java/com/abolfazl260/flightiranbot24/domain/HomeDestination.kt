package com.abolfazl260.flightiranbot24.domain

/**
 * Pure Kotlin destination model: no Android Context, resource IDs, Activities
 * or service-provider details enter the domain layer.
 */
internal enum class HomeDestination {
    OFFLINE_AIRPORTS,
    OFFLINE_CHECKLIST,
    TELEGRAM_BOT,
    TELEGRAM_VISA,
    TELEGRAM_AIRPORTS,
    TELEGRAM_USEFUL,
    SUPPORT,
    PRIVACY,
}

internal data class HomeSections(
    val offline: List<HomeDestination>,
    val online: List<HomeDestination>,
) {
    init {
        require(offline.isNotEmpty()) { "At least one offline action is required" }
        val all = offline + online
        require(all.size == all.distinct().size) { "Duplicate launcher actions" }
    }
}

internal interface HomeRepository {
    suspend fun loadHomeSections(): HomeSections
}
