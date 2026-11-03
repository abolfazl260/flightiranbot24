package com.abolfazl260.flightiranbot24.data.visa

import java.text.Normalizer
import java.util.Locale

/** ISO codes are presentation metadata, not a substitute for the actual visa JSON rules. */
internal object VisaCountries {
    private val persian = Locale.forLanguageTag("fa-IR")
    private val english = Locale.ENGLISH
    private val names = mapOf(
        "IR" to "ایران", "TR" to "ترکیه", "AE" to "امارات", "DE" to "آلمان",
        "TH" to "تایلند", "GE" to "گرجستان", "MY" to "مالزی",
        "AF" to "افغانستان", "IQ" to "عراق", "SA" to "عربستان",
        "GB" to "بریتانیا", "US" to "آمریکا", "FR" to "فرانسه",
        "IT" to "ایتالیا", "CA" to "کانادا", "RU" to "روسیه",
        "AZ" to "آذربایجان", "AM" to "ارمنستان", "QA" to "قطر",
        "OM" to "عمان", "CN" to "چین", "JP" to "ژاپن",
        "IN" to "هند", "PK" to "پاکستان", "AU" to "استرالیا",
    )
    val popular = listOf("TR", "AE", "DE", "TH", "GE", "MY")
    private val isoCodes = Locale.getISOCountries().sorted()

    fun name(code: String): String {
        if (!Regex("[A-Z]{2}").matches(code)) return code
        return names[code] ?: Locale("", code).getDisplayCountry(persian)
            .takeUnless { it.isBlank() || it.equals(code, ignoreCase = true) } ?: code
    }

    fun englishName(code: String): String =
        Locale("", code).getDisplayCountry(english)

    fun allPassportCodes(): List<String> = isoCodes.sortedBy(::name)

    fun flag(code: String): String {
        if (!Regex("[A-Z]{2}").matches(code)) return "🌐"
        val first = Character.toChars(0x1F1E6 + code[0].code - 'A'.code)
        val second = Character.toChars(0x1F1E6 + code[1].code - 'A'.code)
        return String(first) + String(second)
    }

    fun normalize(value: String): String {
        val cleaned = Normalizer.normalize(value, Normalizer.Form.NFKC)
            .lowercase(persian)
            .replace('ي', 'ی').replace('ك', 'ک')
            .replace('ۀ', 'ه').replace('ة', 'ه')
            .replace('\u200c', ' ')
            .replace(Regex("[\u064B-\u065F\u0670]"), "")
        return cleaned.trim().replace(Regex("\\s+"), " ")
    }

    fun matches(code: String, upstreamName: String, query: String): Boolean {
        val term = normalize(query)
        return term.isEmpty() ||
            listOf(code, name(code), englishName(code), upstreamName)
                .any { normalize(it).contains(term) }
    }
}
