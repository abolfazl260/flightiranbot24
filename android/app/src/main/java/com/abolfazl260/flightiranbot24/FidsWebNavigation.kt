package com.abolfazl260.flightiranbot24

import java.net.URI

/** Only the official FIDS origin may be used for top-level in-app navigation. */
internal const val FIDS_OFFICIAL_HOME = "https://fids.airport.ir/"

internal fun isAllowedFidsNavigation(url: String): Boolean = runCatching {
    val uri = URI(url)
    uri.scheme.equals("https", ignoreCase = true) &&
        uri.host.equals("fids.airport.ir", ignoreCase = true) &&
        uri.rawUserInfo == null &&
        (uri.port == -1 || uri.port == 443)
}.getOrDefault(false)
