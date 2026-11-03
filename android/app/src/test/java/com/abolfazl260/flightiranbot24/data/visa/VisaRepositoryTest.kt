package com.abolfazl260.flightiranbot24.data.visa

import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class VisaRepositoryTest {
    private val rule = """
        {"passport":"IR","destination":"TR","country_name":"Turkey",
         "status":"visa-free","stay_days":null,"notes":"Check with the issuing authority.",
         "source_url":"https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa",
         "verified_on":"2026-10-20","source_level":"row",
         "published_at":"2026-11-02T11:05:00.000Z"}
    """.trimIndent()

    private fun json(input: String) = JsonParser.parseString(input).asJsonObject

    @Test fun consumesExactExistingWorkerProjection() = runBlocking {
        val seen = mutableListOf<String>()
        val api = object : PublicJsonRepository<JsonObject> {
            override suspend fun fetch(relativePath: String): NetworkResult<JsonObject> {
                seen += relativePath
                return NetworkResult.Success(
                    if (relativePath.contains("/list?"))
                        json("""{"passport":"IR","rules":[$rule]}""")
                    else json(rule)
                )
            }
        }
        val repo = VisaRepository(api)
        val listing = repo.list("IR") as VisaFetch.Ready
        assertEquals("visa-free", listing.value.single().rawStatus)
        val detailed = (repo.detail("IR", "TR") as VisaFetch.Ready).value
        assertEquals(VisaStatus.FREE, detailed.status)
        assertEquals("2026-10-20", detailed.verifiedOn)
        assertEquals("2026-11-02T11:05:00.000Z", detailed.publishedAt)
        assertNull(detailed.stayDays)
        assertEquals("row", detailed.sourceLevel)
        assertEquals("https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa", detailed.sourceUrl)
        assertEquals(
            listOf("api/v1/visa/list?passport=IR", "api/v1/visa/rule?passport=IR&destination=TR"),
            seen,
        )
    }

    @Test fun allDocumentedStatusesStayDistinctAndUnknownNeverMeansFree() {
        val names = listOf(
            "visa-free", "freedom-of-movement", "evisa", "eta", "visa-on-arrival",
            "embassy-visa", "travel-permit", "banned", "unconfirmed"
        )
        assertEquals(9, names.map(VisaStatus::from).distinct().size)
        assertEquals(VisaStatus.BANNED, VisaStatus.from("banned"))
        assertEquals(VisaStatus.UNCONFIRMED, VisaStatus.from("unconfirmed"))
        assertEquals(VisaStatus.UNKNOWN, VisaStatus.from("new-upstream-value"))
        assertFalse(VisaStatus.UNKNOWN == VisaStatus.FREE)
    }

    @Test fun rejectsMismatchedCountriesAndInvalidStayWithoutInventingValues() {
        val repo = VisaRepository(null)
        assertNull(repo.parseRule(json(rule), "AF", "TR"))
        assertNull(repo.parseRule(json(rule), "IR", "DE"))
        assertNull(repo.parseRule(json(rule.replace("\"stay_days\":null", "\"stay_days\":0")), "IR", "TR"))
        assertEquals(
            VisaStatus.UNKNOWN,
            repo.parseRule(json(rule.replace("visa-free", "undetermined")), "IR", "TR")?.status,
        )
    }

    @Test fun rejectsUnsafeSourceAndMissingOrInvalidVerificationDates() {
        val repo = VisaRepository(null)
        val bad = rule
            .replace("https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa", "javascript:alert(1)")
            .replace("2026-10-20", "2026-55-99")
        val parsed = repo.parseRule(json(bad), "IR", "TR")!!
        assertNull(parsed.sourceUrl)
        assertNull(parsed.verifiedOn)
        assertEquals("2026-11-02T11:05:00.000Z", parsed.publishedAt)
        assertNull(VisaRepository.safeSource("https://person:secret@example.com/"))
        assertNull(VisaRepository.safeSource("http://example.com/"))
    }

    @Test fun classifiesTransportFailuresAndRejectsArbitraryCountryCode() = runBlocking {
        val failing = object : PublicJsonRepository<JsonObject> {
            override suspend fun fetch(relativePath: String) = NetworkResult.HttpFailure(503)
        }
        assertEquals(VisaFetch.Error(VisaFailure.SERVER), VisaRepository(failing).list("IR"))
        assertEquals(VisaFetch.Error(VisaFailure.INVALID), VisaRepository(failing).list("ir"))
        assertEquals(VisaFetch.Error(VisaFailure.INVALID), VisaRepository(failing).detail("IR", "TUR"))
        assertEquals(VisaFetch.Error(VisaFailure.UNCONFIGURED), VisaRepository(null).detail("IR", "TR"))
    }
}
