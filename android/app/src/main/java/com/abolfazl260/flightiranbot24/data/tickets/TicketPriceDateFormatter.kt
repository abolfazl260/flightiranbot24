package com.abolfazl260.flightiranbot24.data.tickets

import java.time.OffsetDateTime
import java.time.ZoneId

/**
 * Formats the API's real observation timestamp as a Persian-calendar date in Tehran time.
 * Invalid timestamps are omitted by the caller instead of being shown in raw ISO form.
 */
internal fun formatTicketObservedAt(observedAt: String): String? {
    val localDateTime = runCatching {
        OffsetDateTime.parse(observedAt)
            .toInstant()
            .atZone(ZoneId.of("Asia/Tehran"))
    }.getOrNull() ?: return null

    val jalali = gregorianToJalali(
        localDateTime.year,
        localDateTime.monthValue,
        localDateTime.dayOfMonth,
    ) ?: return null

    val months = arrayOf(
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
    )
    val hour = localDateTime.hour.toString().padStart(2, '0').toPersianDigits()
    val minute = localDateTime.minute.toString().padStart(2, '0').toPersianDigits()
    return "${jalali.day.toString().toPersianDigits()} ${months[jalali.month - 1]} " +
        "${jalali.year.toString().toPersianDigits()}، ساعت ${hour}:${minute}"
}

private data class JalaliDate(val year: Int, val month: Int, val day: Int)

/** Gregorian-to-Jalali conversion for modern timestamps (1601–2500). */
private fun gregorianToJalali(year: Int, month: Int, day: Int): JalaliDate? {
    if (year !in 1601..2500 || month !in 1..12 || day !in 1..31) return null

    val monthOffsets = intArrayOf(
        0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334,
    )
    var gy = year - 1600
    var jy = 979
    val gy2 = if (month > 2) gy + 1 else gy
    var days = 365 * gy +
        (gy2 + 3) / 4 -
        (gy2 + 99) / 100 +
        (gy2 + 399) / 400 -
        80 + day + monthOffsets[month - 1]

    jy += 33 * (days / 12053)
    days %= 12053
    jy += 4 * (days / 1461)
    days %= 1461
    if (days > 365) {
        jy += (days - 1) / 365
        days = (days - 1) % 365
    }

    val jalaliMonth: Int
    val jalaliDay: Int
    if (days < 186) {
        jalaliMonth = 1 + days / 31
        jalaliDay = 1 + days % 31
    } else {
        jalaliMonth = 7 + (days - 186) / 30
        jalaliDay = 1 + (days - 186) % 30
    }
    return JalaliDate(jy, jalaliMonth, jalaliDay)
}

internal fun formatPersianDigits(value: Int): String = value.toString().toPersianDigits()

private fun String.toPersianDigits(): String = map { char ->
    if (char in '0'..'9') ('۰'.code + (char - '0')).toChar() else char
}.joinToString("")
