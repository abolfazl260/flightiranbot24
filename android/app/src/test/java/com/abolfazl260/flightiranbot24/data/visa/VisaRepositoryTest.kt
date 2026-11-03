package com.abolfazl260.flightiranbot24.data.visa

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The installed app uses the packaged JSON snapshot, never a visa HTTP endpoint. */
class VisaRepositoryTest {
    private val manifest = """
        {
          "schema_version": 1,
          "license": "CC-BY-4.0",
          "attribution": "TravelRequirements.info (CC BY 4.0)",
          "passports": 2,
          "destinations": 2,
          "rows": 4,
          "passport_codes": ["IR", "AF"],
          "shards": ["shard-00.json"],
          "source_data_modified_on": "2026-10-22"
        }
    """.trimIndent()

    private val shard = """
        {
          "version": 1,
          "destinations": [
            {
              "destination": "TR",
              "country_name": "Turkey",
              "updated_on": "2026-10-11",
              "rules": [
                ["IR", "visa-free", 90, "Confirm rules before travelling.", "https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa", "2026-10-20", "row"],
                ["AF", "embassy-visa", null, null, null, "2026-10-03", "policy"]
              ]
            },
            {
              "destination": "DE",
              "country_name": "Germany",
              "updated_on": "2026-10-20",
              "rules": [
                ["IR", "embassy-visa", null, "Apply at an embassy.", "https://example.org/visa", null, "row"],
                ["AF", "unconfirmed", null, null, null, null, "policy"]
              ]
            }
          ]
        }
    """.trimIndent()

    private fun repository(
        manifestJson: String = manifest,
        shardJson: String = shard,
        requests: MutableList<String>? = null,
    ): VisaRepository = VisaRepository(VisaBundleReader { file ->
        requests?.add(file)
        when (file) {
            "manifest.v1.json" -> manifestJson
            "shard-00.json" -> shardJson
            else -> error("Unexpected bundled file: $file")
        }
    })

    @Test fun readsVisaRulesFromPackagedJsonWithoutNetworkRequests() = runBlocking {
        val requests = mutableListOf<String>()
        val repo = repository(requests = requests)
        val result = repo.list("IR") as VisaFetch.Ready
        assertEquals(listOf("DE", "TR"), result.value.rules.map { it.destination })
        assertEquals(listOf("AF", "IR"), result.value.passportCodes)
        assertEquals("2026-10-22", result.value.sourceDataModifiedOn)
        assertEquals("TravelRequirements.info (CC BY 4.0)", result.value.attribution)
        assertEquals(listOf("manifest.v1.json", "shard-00.json"), requests)

        val detail = (repo.detail("IR", "TR") as VisaFetch.Ready).value
        assertEquals(VisaStatus.FREE, detail.status)
        assertEquals("visa-free", detail.rawStatus)
        assertEquals(90, detail.stayDays)
        assertEquals("2026-10-20", detail.verifiedOn)
        assertEquals("2026-10-11", detail.destinationUpdatedOn)
        assertEquals("row", detail.sourceLevel)
        assertEquals("Turkey", detail.upstreamCountryName)
        assertEquals("https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa", detail.sourceUrl)
        assertEquals(listOf("manifest.v1.json", "shard-00.json"), requests)
    }

    @Test fun selectingAnotherPassportReadsItsOwnRules() = runBlocking {
        val repo = repository()
        val result = repo.list("AF") as VisaFetch.Ready
        val turkey = result.value.rules.single { it.destination == "TR" }
        assertEquals(VisaStatus.EMBASSY, turkey.status)
        assertNull(turkey.stayDays)
        assertEquals("policy", turkey.sourceLevel)
        assertEquals(VisaStatus.UNCONFIRMED,
            (repo.detail("AF", "DE") as VisaFetch.Ready).value.status)
    }

    @Test fun allDocumentedStatusesRemainDistinctAndUnknownNeverMeansFree() {
        val names = listOf(
            "visa-free", "freedom-of-movement", "evisa", "eta", "visa-on-arrival",
            "embassy-visa", "travel-permit", "banned", "unconfirmed",
        )
        assertEquals(9, names.map(VisaStatus::from).distinct().size)
        assertEquals(VisaStatus.BANNED, VisaStatus.from("banned"))
        assertEquals(VisaStatus.UNCONFIRMED, VisaStatus.from("unconfirmed"))
        assertEquals(VisaStatus.UNKNOWN, VisaStatus.from("new-upstream-value"))
        assertFalse(VisaStatus.UNKNOWN == VisaStatus.FREE)
    }

    @Test fun rejectsInvalidPassportAndMissingDestination() = runBlocking {
        val repo = repository()
        assertEquals(VisaFetch.Error(VisaFailure.NOT_FOUND), repo.list("ir"))
        assertEquals(VisaFetch.Error(VisaFailure.NOT_FOUND), repo.list("FR"))
        assertEquals(VisaFetch.Error(VisaFailure.NOT_FOUND), repo.detail("IR", "TUR"))
        assertEquals(VisaFetch.Error(VisaFailure.NOT_FOUND), repo.detail("IR", "US"))
    }

    @Test fun invalidStayOrIncompleteMatrixFailsClosed() = runBlocking {
        val invalidStay = shard.replace(
            "[\"IR\", \"visa-free\", 90", "[\"IR\", \"visa-free\", 0",
        )
        assertEquals(
            VisaFetch.Error(VisaFailure.INVALID),
            repository(shardJson = invalidStay).list("IR"),
        )
        val missingPassportRule = shard.replace(
            "[\"AF\", \"embassy-visa\", null, null, null, \"2026-10-03\", \"policy\"]", 
            "",
        )
        assertEquals(
            VisaFetch.Error(VisaFailure.INVALID),
            repository(shardJson = missingPassportRule).list("IR"),
        )
        val duplicateDestination = shard.replace(
            "\"destination\": \"DE\"", "\"destination\": \"TR\"",
        )
        assertEquals(
            VisaFetch.Error(VisaFailure.INVALID),
            repository(shardJson = duplicateDestination).list("IR"),
        )
    }

    @Test fun rejectsUnsafeSourceAndInvalidVerificationDateWithoutMakingUpValues() = runBlocking {
        val changed = shard
            .replace("https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa", "javascript:alert(1)")
            .replace("2026-10-20", "2026-55-99")
        val rule = (repository(shardJson = changed).detail("IR", "TR") as VisaFetch.Ready).value
        assertNull(rule.sourceUrl)
        assertNull(rule.verifiedOn)
        assertNull(VisaRepository.safeSource("https://person:secret@example.com/"))
        assertNull(VisaRepository.safeSource("http://example.com/"))
        assertEquals(VisaStatus.FREE, rule.status)
    }

    @Test fun rejectsUnexpectedBundleVersionAndUnreadableShard() = runBlocking {
        assertEquals(
            VisaFetch.Error(VisaFailure.INVALID),
            repository(manifestJson = manifest.replace("\"schema_version\": 1", "\"schema_version\": 2"))
                .list("IR"),
        )
        val reader = VisaBundleReader { file ->
            if (file == "manifest.v1.json") manifest else error("Missing APK asset")
        }
        assertEquals(VisaFetch.Error(VisaFailure.INVALID), VisaRepository(reader).list("IR"))
    }

    @Test fun unrecognizedSourceStatusRemainsUnknown() = runBlocking {
        val changed = shard.replace("\"visa-free\"", "\"new-upstream-value\"")
        val rule = (repository(shardJson = changed).detail("IR", "TR") as VisaFetch.Ready).value
        assertEquals(VisaStatus.UNKNOWN, rule.status)
        assertEquals("new-upstream-value", rule.rawStatus)
        assertTrue(rule.stayDays == 90)
    }
}
