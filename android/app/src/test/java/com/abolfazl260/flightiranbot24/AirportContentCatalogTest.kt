package com.abolfazl260.flightiranbot24

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class AirportContentCatalogTest {
    private val index = """
      {"schema_version":1,"airports":[
        {"iata":"THR","detail_path":"details/THR.v1.json","enabled":true},
        {"iata":"MHD","detail_path":"details/MHD.v1.json","enabled":false}
      ]}
    """.trimIndent()

    private val detail = """
      {"schema_version":1,"iata":"THR","sections":[
        {"id":"airport-videos","title_fa":"ویدیو فرودگاه","icon":"video","order":50,
         "status":"draft","reviewed_at":null,"source_urls":[],"blocks":[]},
        {"id":"parking","title_fa":"پارکینگ","icon":"car","order":10,
         "status":"published","reviewed_at":"2026-11-03T12:00:00Z",
         "source_urls":["https://example.org/parking"],
         "blocks":[
           {"type":"text","text_fa":"راهنمای پارکینگ"},
           {"type":"link","title_fa":"منبع","url":"https://example.org/parking"},
           {"type":"future_widget","url":"javascript:alert(1)"}
         ]},
        {"id":"traveler-experiences","title_fa":"تجربه کاربران","icon":"message-square",
         "order":20,"status":"published","reviewed_at":"2026-11-03T12:00:00Z",
         "source_urls":[],
         "blocks":[{"type":"experience","id":"review-1","text_fa":"خوب بود",
           "rating":4,"visit_date":"2026-10-01","approved":true}]}
      ]}
    """.trimIndent()

    @Test fun indexOnlyRevealsEnabledAirports() {
        val result = AirportContentParser.parseIndex(index)
        assertEquals(1, result.airports.size)
        assertEquals("THR", result.airports.single().iata)
    }

    @Test fun arbitraryNewSectionsWorkAndDraftsStayHidden() {
        val result = AirportContentParser.parseDetail(detail, "THR")
        assertEquals(listOf("parking", "traveler-experiences"), result.sections.map { it.id })
        assertEquals(2, result.sections.first().blocks.size)
        assertTrue(result.sections.first().blocks.first() is AirportContentBlock.Text)
        assertTrue(result.sections.last().blocks.single() is AirportContentBlock.Experience)
    }

    @Test fun rejectsCrossAirportContentAndUnsafePath() {
        assertThrows(IllegalArgumentException::class.java) {
            AirportContentParser.parseDetail(detail, "MHD")
        }
        assertThrows(IllegalArgumentException::class.java) {
            AirportContentParser.parseIndex(
                index.replace("details/THR.v1.json", "../private.json")
            )
        }
    }

    @Test fun rejectsUnsafePublishedLinks() {
        assertThrows(IllegalArgumentException::class.java) {
            AirportContentParser.parseDetail(
                detail.replace("https://example.org/parking", "http://example.org/parking"), "THR"
            )
        }
    }

    @Test fun ignoresUnknownBlockTypesButNotUnapprovedReviews() {
        assertFalse(AirportContentParser.parseDetail(detail, "THR").sections.isEmpty())
        assertThrows(IllegalArgumentException::class.java) {
            AirportContentParser.parseDetail(
                detail.replace("\"approved\":true", "\"approved\":false"), "THR"
            )
        }
    }

    @Test fun rejectsDuplicateSectionIds() {
        assertThrows(IllegalArgumentException::class.java) {
            AirportContentParser.parseDetail(
                detail.replace("\"id\":\"traveler-experiences\"", "\"id\":\"parking\""), "THR"
            )
        }
    }
}
