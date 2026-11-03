package com.abolfazl260.flightiranbot24.data.visa

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject
import java.net.URI
import java.time.LocalDate
import java.time.OffsetDateTime
import kotlinx.coroutines.CancellationException

/** Data from the existing passport-specific public JSON projection. No eligibility is inferred. */
internal data class VisaRule(
    val passport: String,
    val destination: String,
    val upstreamCountryName: String,
    val status: VisaStatus,
    val rawStatus: String,
    val stayDays: Int?,
    val notes: String?,
    val sourceUrl: String?,
    val verifiedOn: String?,
    val sourceLevel: String?,
    val publishedAt: String?,
)

internal enum class VisaStatus(val persianLabel: String) {
    FREE("بدون نیاز به ویزا"),
    MOVEMENT("آزادی تردد"),
    EVISA("ویزای الکترونیکی"),
    ETA("مجوز الکترونیکی سفر"),
    ARRIVAL("ویزای فرودگاهی"),
    EMBASSY("ویزای سفارت"),
    PERMIT("مجوز سفر"),
    BANNED("محدودیت یا ممنوعیت ورود"),
    UNCONFIRMED("وضعیت تأییدنشده"),
    UNKNOWN("وضعیت نامشخص");

    companion object {
        fun from(value: String): VisaStatus = when (value.lowercase()) {
            "visa-free" -> FREE
            "freedom-of-movement" -> MOVEMENT
            "evisa" -> EVISA
            "eta" -> ETA
            "visa-on-arrival" -> ARRIVAL
            "embassy-visa" -> EMBASSY
            "travel-permit" -> PERMIT
            "banned" -> BANNED
            "unconfirmed" -> UNCONFIRMED
            else -> UNKNOWN
        }
    }
}

internal enum class VisaFailure { UNCONFIGURED, OFFLINE, TIMEOUT, NOT_FOUND, SERVER, INVALID }
internal sealed interface VisaFetch<out T> {
    data class Ready<T>(val value: T) : VisaFetch<T>
    data class Error(val reason: VisaFailure) : VisaFetch<Nothing>
}

/**
 * Consumes the same published JSON originally indexed from the visa destination data.
 * The generic network client's URL validator allows ONLY these two fixed, bounded query forms.
 */
internal class VisaRepository(private val api: PublicJsonRepository<JsonObject>?) {
    private val code = Regex("[A-Z]{2}")

    suspend fun list(passport: String): VisaFetch<List<VisaRule>> {
        if (!code.matches(passport)) return VisaFetch.Error(VisaFailure.INVALID)
        return request("api/v1/visa/list?passport=" + passport) { payload ->
            if (payload.string("passport") != passport) return@request null
            val entries = payload.get("rules")?.takeIf { it.isJsonArray }?.asJsonArray ?: return@request null
            if (entries.size() == 0 || entries.size() > 250) return@request null
            val parsed = entries.map { item ->
                item.takeIf { it.isJsonObject }?.asJsonObject?.let {
                    parseRule(it, passport, null)
                } ?: return@request null
            }
            if (parsed.map { it.destination }.distinct().size != parsed.size) return@request null
            parsed
        }
    }

    suspend fun detail(passport: String, destination: String): VisaFetch<VisaRule> {
        if (!code.matches(passport) || !code.matches(destination)) {
            return VisaFetch.Error(VisaFailure.INVALID)
        }
        return request("api/v1/visa/rule?passport=" + passport + "&destination=" + destination) {
            parseRule(it, passport, destination)
        }
    }

    private suspend fun <T> request(
        path: String,
        parser: (JsonObject) -> T?,
    ): VisaFetch<T> {
        val client = api ?: return VisaFetch.Error(VisaFailure.UNCONFIGURED)
        return try {
            when (val response = client.fetch(path)) {
                is NetworkResult.Success ->
                    parser(response.value)?.let { VisaFetch.Ready(it) }
                        ?: VisaFetch.Error(VisaFailure.INVALID)
                is NetworkResult.HttpFailure -> when (response.statusCode) {
                    404 -> VisaFetch.Error(VisaFailure.NOT_FOUND)
                    503 -> VisaFetch.Error(VisaFailure.SERVER)
                    else -> VisaFetch.Error(VisaFailure.SERVER)
                }
                NetworkResult.Timeout -> VisaFetch.Error(VisaFailure.TIMEOUT)
                NetworkResult.ConnectionFailure -> VisaFetch.Error(VisaFailure.OFFLINE)
                else -> VisaFetch.Error(VisaFailure.INVALID)
            }
        } catch (cancel: CancellationException) {
            throw cancel
        } catch (_: Exception) {
            VisaFetch.Error(VisaFailure.INVALID)
        }
    }

    internal fun parseRule(
        payload: JsonObject,
        passport: String,
        destination: String?,
    ): VisaRule? {
        val actualPassport = payload.string("passport") ?: return null
        val actualDestination = payload.string("destination") ?: return null
        if (actualPassport != passport || !code.matches(actualDestination) ||
            (destination != null && actualDestination != destination)
        ) return null
        val country = payload.string("country_name") ?: return null
        val rawStatus = payload.string("status") ?: return null
        val stay = payload.get("stay_days")?.let {
            if (it.isJsonNull) null
            else if (it.isJsonPrimitive && it.asJsonPrimitive.isNumber) {
                runCatching { it.asInt }.getOrNull()?.takeIf { n -> n in 1..36500 }
                    ?: return null
            } else return null
        }
        val verified = payload.string("verified_on")?.takeIf {
            runCatching { LocalDate.parse(it) }.isSuccess
        }
        val published = payload.string("published_at")?.takeIf {
            runCatching { OffsetDateTime.parse(it) }.isSuccess
        }
        return VisaRule(
            passport = actualPassport,
            destination = actualDestination,
            upstreamCountryName = country,
            status = VisaStatus.from(rawStatus),
            rawStatus = rawStatus,
            stayDays = stay,
            notes = payload.string("notes"),
            sourceUrl = safeSource(payload.string("source_url")),
            verifiedOn = verified,
            sourceLevel = payload.string("source_level"),
            publishedAt = published,
        )
    }

    companion object {
        private fun JsonObject.string(key: String): String? {
            val value = get(key) ?: return null
            if (!value.isJsonPrimitive || !value.asJsonPrimitive.isString) return null
            return value.asString.trim().takeIf { it.isNotBlank() }
        }

        fun safeSource(value: String?): String? {
            if (value.isNullOrBlank() || value.length > 900 ||
                value.any { it.code < 32 }
            ) return null
            return runCatching {
                val uri = URI(value)
                value.takeIf {
                    uri.scheme.equals("https", ignoreCase = false) &&
                        !uri.host.isNullOrBlank() && uri.rawUserInfo == null
                }
            }.getOrNull()
        }
    }
}
