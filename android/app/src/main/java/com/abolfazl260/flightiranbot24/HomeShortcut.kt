package com.abolfazl260.flightiranbot24

/**
 * The Android launcher provides native/offline travel tools, and deliberately
 * hands off other capabilities to Telegram until AND-002 / API-001 are ready.
 * Do not put bot tokens or Telegram initData in this application.
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

internal data class HomeShortcut(
    val destination: HomeDestination,
    val labelRes: Int,
)

internal val offlineHomeShortcuts = listOf(
    HomeShortcut(HomeDestination.OFFLINE_AIRPORTS, R.string.offline_airports),
    HomeShortcut(HomeDestination.OFFLINE_CHECKLIST, R.string.checklist_title),
)

internal val onlineHomeShortcuts = listOf(
    HomeShortcut(HomeDestination.TELEGRAM_BOT, R.string.open_bot),
    HomeShortcut(HomeDestination.TELEGRAM_VISA, R.string.open_visa),
    HomeShortcut(HomeDestination.TELEGRAM_AIRPORTS, R.string.open_airports),
    HomeShortcut(HomeDestination.TELEGRAM_USEFUL, R.string.open_useful),
    HomeShortcut(HomeDestination.SUPPORT, R.string.open_support),
    HomeShortcut(HomeDestination.PRIVACY, R.string.open_privacy),
)
