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


/** Explain upstream HTTP failures without claiming the flight itself was cancelled. */
internal fun fidsHttpStatusMessage(code: Int): String = when (code) {
    401, 403 -> "سامانه اطلاعات پرواز دسترسی به این درخواست را نپذیرفت (خطای $code). ممکن است محدودیت دسترسی وجود داشته باشد."
    404 -> "صفحه اطلاعات پرواز در سایت رسمی پیدا نشد (خطای ۴۰۴)."
    408, 504 -> "پاسخ سامانه اطلاعات پرواز با تأخیر مواجه شد (خطای $code). لطفاً دوباره تلاش کنید."
    429 -> "تعداد درخواست‌ها به سامانه بیش از حد مجاز است (خطای ۴۲۹). لطفاً کمی بعد تلاش کنید."
    in 500..599 -> "سرور سامانه اطلاعات پرواز در حال حاضر پاسخ مناسبی نمی‌دهد (خطای $code). لطفاً بعداً تلاش کنید."
    else -> "سامانه اطلاعات پرواز خطای $code برگرداند. لطفاً دوباره تلاش کنید."
}
