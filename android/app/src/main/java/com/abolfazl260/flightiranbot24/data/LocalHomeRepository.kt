package com.abolfazl260.flightiranbot24.data

import com.abolfazl260.flightiranbot24.domain.HomeDestination
import com.abolfazl260.flightiranbot24.domain.HomeRepository
import com.abolfazl260.flightiranbot24.domain.HomeSections

/**
 * Device-local navigation catalogue; this task does not make any network
 * requests or claim Telegram features have a native Android API yet.
 */
internal class LocalHomeRepository : HomeRepository {
    override suspend fun loadHomeSections() = HomeSections(
        offline = listOf(
            HomeDestination.OFFLINE_AIRPORTS,
            HomeDestination.OFFLINE_CHECKLIST,
        ),
        online = listOf(
            HomeDestination.TELEGRAM_BOT,
            HomeDestination.TELEGRAM_VISA,
            HomeDestination.TELEGRAM_AIRPORTS,
            HomeDestination.TELEGRAM_USEFUL,
            HomeDestination.SUPPORT,
            HomeDestination.PRIVACY,
        ),
    )
}
