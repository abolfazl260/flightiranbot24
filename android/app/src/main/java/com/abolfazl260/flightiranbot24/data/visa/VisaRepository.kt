package com.abolfazl260.flightiranbot24.data.visa

import android.content.Context
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.net.URI
import java.time.LocalDate
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

/** Frozen, source-attributed rules bundled in the APK; there is no visa network request. */
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
    val destinationUpdatedOn: String?,
)

internal data class OfflineVisaCatalog(
    val rules: List<VisaRule>,
    val passportCodes: List<String>,
    val sourceDataModifiedOn: String?,
    val attribution: String,
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

internal enum class VisaFailure { NOT_FOUND, INVALID }
internal sealed interface VisaFetch<out T> {
    data class Ready<T>(val value: T) : VisaFetch<T>
    data class Error(val reason: VisaFailure) : VisaFetch<Nothing>
}

/** Injected bundle reader lets JVM tests verify everything without a network or Android device. */
internal fun interface VisaBundleReader {
    fun read(file: String): String
}

internal class AndroidVisaBundleReader(private val context: Context) : VisaBundleReader {
    override fun read(file: String): String {
        require(file == "manifest.v1.json" || Regex("shard-[0-9]{2}\\.json").matches(file))
        return context.assets.open("visa/$file").bufferedReader(Charsets.UTF_8).use { it.readText() }
    }
}

/**
 * Fixed 20-shard compact snapshot extracted from the upstream destination JSON files.
 * We parse all shards on an IO dispatcher, retain only one passport's 199 rules, and
 * cache that passport in memory. No Cloudflare, bot SQLite or runtime provider access.
 */
internal class VisaRepository(private val reader: VisaBundleReader) {
    private val code = Regex("[A-Z]{2}")
    private val lock = Mutex()
    private var cachedPassport: String? = null
    private var cachedCatalog: OfflineVisaCatalog? = null

    suspend fun list(passport: String): VisaFetch<OfflineVisaCatalog> {
        if (!code.matches(passport)) return VisaFetch.Error(VisaFailure.NOT_FOUND)
        return try {
            withContext(Dispatchers.IO) {
                lock.withLock {
                    if (cachedPassport == passport && cachedCatalog != null) {
                        return@withLock VisaFetch.Ready(cachedCatalog!!)
                    }
                    val catalog = readCatalog(passport) ?: return@withLock VisaFetch.Error(VisaFailure.NOT_FOUND)
                    cachedPassport = passport
                    cachedCatalog = catalog
                    VisaFetch.Ready(catalog)
                }
            }
        } catch (cancel: CancellationException) {
            throw cancel
        } catch (_: Exception) {
            VisaFetch.Error(VisaFailure.INVALID)
        }
    }

    suspend fun detail(passport: String, destination: String): VisaFetch<VisaRule> {
        if (!code.matches(destination)) return VisaFetch.Error(VisaFailure.NOT_FOUND)
        return when (val result = list(passport)) {
            is VisaFetch.Error -> result
            is VisaFetch.Ready -> result.value.rules.find { it.destination == destination }
                ?.let { VisaFetch.Ready(it) } ?: VisaFetch.Error(VisaFailure.NOT_FOUND)
        }
    }

    private fun readCatalog(passport: String): OfflineVisaCatalog? {
        val manifest = JsonParser.parseString(reader.read("manifest.v1.json")).asJsonObject
        if (manifest.number("schema_version") != 1 ||
            manifest.string("license") != "CC-BY-4.0") error("Unsupported offline visa bundle")
        val passports = manifest.get("passport_codes")?.asJsonArray?.map { it.asString }
            ?: error("Missing passport registry")
        val expectedPassportCount = manifest.number("passports") ?: error("Missing passport count")
        val expectedDestinations = manifest.number("destinations") ?: error("Missing destination count")
        val expectedRows = manifest.number("rows") ?: error("Missing row count")
        if (passports.size != expectedPassportCount || passports.toSet().size != passports.size ||
            passports.any { !code.matches(it) } || expectedDestinations !in 1..250 ||
            expectedPassportCount !in 1..250 || expectedRows != expectedDestinations * expectedPassportCount
        ) error("Invalid offline visa coverage")
        if (passport !in passports) return null
        val shards = manifest.get("shards")?.asJsonArray?.map { it.asString }
            ?: error("Missing offline shards")
        if (shards.isEmpty() || shards.size > 40 || shards.size != shards.distinct().size ||
            shards.any { !Regex("shard-[0-9]{2}\\.json").matches(it) }
        ) error("Invalid bundle file list")

        val results = ArrayList<VisaRule>(expectedDestinations)
        val destinations = HashSet<String>()
        var rowsSeen = 0
        for (shard in shards) {
            val payload = JsonParser.parseString(reader.read(shard)).asJsonObject
            if (payload.number("version") != 1) error("Invalid offline shard version")
            val entries = payload.get("destinations")?.asJsonArray ?: error("Missing destination rows")
            for (entry in entries) {
                if (!entry.isJsonObject) error("Malformed destination")
                val destination = entry.asJsonObject
                val destinationCode = destination.string("destination") ?: error("Missing destination ISO")
                if (!code.matches(destinationCode) || !destinations.add(destinationCode)) {
                    error("Duplicate/invalid visa destination")
                }
                val countryName = destination.string("country_name") ?: error("Missing country name")
                val updatedOn = safeDate(destination.string("updated_on"))
                val rules = destination.get("rules")?.asJsonArray ?: error("Missing passport matrix")
                if (rules.size() != expectedPassportCount) error("Incomplete passport matrix")
                rowsSeen += rules.size()
                val matches = rules.mapNotNull {
                    val row = it.takeIf { value -> value.isJsonArray }?.asJsonArray
                        ?: error("Malformed visa row")
                    if (row.size() != 7) error("Invalid visa rule tuple")
                    val rowPassport = row.text(0) ?: error("Missing row passport")
                    if (!code.matches(rowPassport)) error("Invalid row passport")
                    if (rowPassport != passport) null else parseRow(
                        row, passport, destinationCode, countryName, updatedOn
                    )
                }
                if (matches.size != 1) error("Missing/duplicate passport entry")
                results.add(matches.single())
            }
        }
        if (results.size != expectedDestinations || rowsSeen != expectedRows) {
            error("Incomplete offline visa snapshot")
        }
        return OfflineVisaCatalog(
            rules = results.sortedBy { it.destination },
            passportCodes = passports.sorted(),
            sourceDataModifiedOn = safeDate(manifest.string("source_data_modified_on")),
            attribution = manifest.string("attribution") ?: error("Missing attribution"),
        )
    }

    private fun parseRow(
        row: JsonArray,
        passport: String,
        destination: String,
        countryName: String,
        updatedOn: String?,
    ): VisaRule {
        val status = row.text(1) ?: "unknown"
        val stay = row.get(2).takeUnless { it.isJsonNull }?.let {
            if (!it.isJsonPrimitive || !it.asJsonPrimitive.isNumber) error("Invalid stay days")
            it.asInt.takeIf { value -> value in 1..36500 }
                ?: error("Invalid stay days")
        }
        return VisaRule(
            passport = passport,
            destination = destination,
            upstreamCountryName = countryName,
            status = VisaStatus.from(status),
            rawStatus = status,
            stayDays = stay,
            notes = row.text(3),
            sourceUrl = safeSource(row.text(4)),
            verifiedOn = safeDate(row.text(5)),
            sourceLevel = row.text(6),
            destinationUpdatedOn = updatedOn,
        )
    }

    companion object {
        private fun JsonObject.string(key: String): String? {
            val value = get(key) ?: return null
            if (value.isJsonNull || !value.isJsonPrimitive || !value.asJsonPrimitive.isString) return null
            return value.asString.trim().takeIf { it.isNotBlank() }
        }

        private fun JsonObject.number(key: String): Int? {
            val value = get(key) ?: return null
            if (!value.isJsonPrimitive || !value.asJsonPrimitive.isNumber) return null
            return runCatching { value.asInt }.getOrNull()
        }

        private fun JsonArray.text(index: Int): String? {
            val value = get(index)
            if (value.isJsonNull || !value.isJsonPrimitive || !value.asJsonPrimitive.isString) return null
            return value.asString.trim().takeIf { it.isNotBlank() }
        }

        private fun safeDate(value: String?): String? =
            value?.takeIf { runCatching { LocalDate.parse(it) }.isSuccess }

        fun safeSource(value: String?): String? {
            if (value.isNullOrBlank() || value.length > 900 || value.any { it.code < 32 }) return null
            return runCatching {
                val uri = URI(value)
                value.takeIf {
                    uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.rawUserInfo == null
                }
            }.getOrNull()
        }
    }
}
