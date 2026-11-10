package com.abolfazl260.flightiranbot24

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.time.Instant
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class AirlineContentTest {
    private val context: Context get() = ApplicationProvider.getApplicationContext()
    private val now = Instant.parse("2026-11-11T00:00:00Z")
    private fun bundled(path: String) = context.assets.open(path).bufferedReader().use { it.readText() }
    private fun page() = JsonParser.parseString(bundled("details/emirates.v1.json")).asJsonObject
    private fun parse(root: JsonObject) = AirlineContentParser.detail(root.toString(), "emirates", now)!!
    private fun rejected(action: () -> Unit) {
        try { action(); fail("Unsafe content accepted") } catch (_: IllegalArgumentException) { }
    }

    @Test fun bundledCatalogHasIndependentPagesAndNoSyntheticRatings() {
        val rows = AirlineContentParser.index(bundled("airline-index.v1.json"), now)
        assertEquals(setOf("iran-air", "emirates"), rows.map { it.id }.toSet())
        assertEquals(1, AirlineContentParser.detail(bundled("details/iran-air.v1.json"), "iran-air", now)!!.sections.size)
        val page = parse(page())
        assertEquals(10, page.sections.size)
        assertTrue(page.sections.map { it.id }.containsAll(listOf("cabin", "catering", "special-assistance")))
        assertEquals(0, page.ratingCount)
        assertNull(page.average)
        val fleet = page.sections.flatMap { it.blocks }.filterIsInstance<AirlineBlock.Fleet>()
        assertEquals(listOf("A350", "A380", "777"), fleet.map { it.model })
        assertTrue(fleet.all { it.count == null && it.relationship == "operated" })
    }

    @Test fun arabicPersianLatinCodesAndAliasesAreSearchable() {
        val rows = AirlineContentParser.index(bundled("airline-index.v1.json"), now)
        assertEquals("iran-air", filterAirlines(rows, "ايران اير", "iran").single().id)
        assertEquals("iran-air", filterAirlines(rows, "هما", "all").single().id)
        assertEquals("emirates", filterAirlines(rows, "uae", "foreign").single().id)
        assertTrue(filterAirlines(rows, "EK", "iran").isEmpty())
    }

    @Test fun draftArchivedStaleAndExpiredContentAreNeverRendered() {
        val root = page()
        root.getAsJsonObject("metadata").addProperty("status", "archived")
        assertNull(AirlineContentParser.detail(root.toString(), "emirates", now))
        val fresh = page()
        fresh.getAsJsonArray("sections")[0].asJsonObject.getAsJsonObject("metadata").addProperty("stale", true)
        assertFalse(parse(fresh).sections.any { it.id == "baggage" })
        val meta = fresh.getAsJsonArray("sections")[1].asJsonObject.getAsJsonObject("metadata")
        meta.addProperty("effective_to", "2026-11-01T00:00:00Z")
        assertFalse(parse(fresh).sections.any { it.id == "ticket-rules" })
        val directory = JsonParser.parseString(bundled("airline-index.v1.json")).asJsonObject
        directory.getAsJsonArray("airlines")[0].asJsonObject.getAsJsonObject("metadata").addProperty("status", "draft")
        assertEquals(listOf("emirates"), AirlineContentParser.index(directory.toString(), now).map { it.id })
    }

    @Test fun unknownBlocksAreSkippedWithoutCrashingOrBlankCards() {
        val root = page()
        val section = root.getAsJsonArray("sections")[0].asJsonObject
        section.add("blocks", JsonParser.parseString("""[{"type":"future_renderer"}]"""))
        assertFalse(parse(root).sections.any { it.id == "baggage" })
    }

    @Test fun identitySourcesDatesMediaAndPathsFailClosed() {
        rejected { AirlineContentParser.detail(page().toString(), "wrong-airline", now) }
        val root = page()
        root.getAsJsonObject("metadata").add("source_urls", JsonParser.parseString("""["http://example.org"]"""))
        rejected { parse(root) }
        rejected { AirlineContentParser.https("https://user:password@example.org/") }
        val future = page()
        future.getAsJsonObject("metadata").addProperty("verified_at", "2099-01-01T00:00:00Z")
        rejected { parse(future) }
        val media = page()
        media.getAsJsonArray("sections")[0].asJsonObject.add("blocks", JsonParser.parseString("""
            [{"type":"image","rights_verified":false,"url":"https://example.org/photo"}]
        """))
        rejected { parse(media) }
    }

    @Test fun policyScopesPreserveRouteFareCabinAndOperatingCarrier() {
        val root = page()
        val scope = root.getAsJsonArray("sections")[0].asJsonObject.getAsJsonObject("scope")
        scope.addProperty("route", "DXB-LHR")
        scope.addProperty("fare_brand", "fixture-fare")
        scope.addProperty("cabin_class", "fixture-cabin")
        scope.addProperty("seller", "agency")
        val parsed = parse(root).sections.first().scope!!
        assertEquals("DXB-LHR", parsed.route)
        assertEquals("fixture-fare", parsed.fare)
        assertEquals("fixture-cabin", parsed.cabin)
        assertEquals("emirates", parsed.operatingCarrier)
        assertEquals("agency", parsed.seller)
    }

    private fun review() = JsonParser.parseString("""
        {"review_id":"fixture-review","airline_id":"emirates","experience_id":null,
         "visit_date":null,"publication_timestamp":"2026-11-04T00:00:00Z",
         "consent_status":"granted","moderation_status":"approved","verified_origin":true,
         "privacy_reviewed":true,"conflict_of_interest":false,"ratings":{"overall":4,"crew":5}}
    """).asJsonObject

    @Test fun criteriaHaveSeparateCountsAndNoUnapprovedMeansOrStars() {
        val root = page()
        root.getAsJsonArray("published_reviews").add(review())
        val parsed = parse(root)
        assertEquals(1, parsed.ratingCount)
        assertEquals(1, parsed.criterionCounts["crew"])
        assertEquals(0, parsed.criterionCounts["seat"])
        assertNull(parsed.average)
        root.getAsJsonArray("published_reviews")[0].asJsonObject.addProperty("consent_status", "unknown")
        assertEquals(0, parse(root).ratingCount)
    }

    @Test fun duplicatesAndFractionalStarsAreRejected() {
        val root = page()
        root.getAsJsonArray("published_reviews").add(review())
        root.getAsJsonArray("published_reviews").add(review())
        rejected { parse(root) }
        val fractional = page()
        val review = review()
        review.getAsJsonObject("ratings").addProperty("overall", 4.5)
        fractional.getAsJsonArray("published_reviews").add(review)
        rejected { parse(fractional) }
    }

    @Test fun unavailableTransportUsesBundledReviewDatesAndSuccessfulArchiveDoesNotResurrect() = runBlocking {
        val server = MockWebServer()
        server.start()
        try {
            val repo = AirlineContentRepository(context, server.url("/").toString())
            server.enqueue(MockResponse().setResponseCode(503))
            val fallback = repo.index()
            assertTrue(fallback.usedBundledFallback)
            assertTrue(fallback.value.all { it.reviewedAt.startsWith("2026-11-04") })
            val archived = page()
            archived.getAsJsonObject("metadata").addProperty("status", "archived")
            server.enqueue(MockResponse().setBody(archived.toString()))
            val loaded = repo.detail(fallback.value.first { it.id == "emirates" })
            assertFalse(loaded.usedBundledFallback)
            assertNull(loaded.value)
            server.enqueue(MockResponse().setBody("broken-json"))
            assertTrue(repo.index().usedBundledFallback)
        } finally { server.shutdown() }
    }
}
