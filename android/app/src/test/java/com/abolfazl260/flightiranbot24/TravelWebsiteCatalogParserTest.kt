package com.abolfazl260.flightiranbot24

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class TravelWebsiteCatalogParserTest {
    private val validCatalog = """
        {
          "schema_version": 1,
          "categories": [
            {"id":"planning", "name_fa":"برنامه‌ریزی سفر", "order":0}
          ],
          "websites": [
            {
              "id":"rome2rio", "name_fa":"روم‌تو‌ریو",
              "description_fa":"مسیرهای حمل‌ونقل",
              "category_id":"planning",
              "url":"https://www.rome2rio.com/",
              "image":"images/rome2rio.webp",
              "order":3, "enabled":true
            },
            {
              "id":"hidden", "name_fa":"غیرفعال",
              "description_fa":"اطلاعات نمایشی",
              "category_id":"planning",
              "url":"https://example.com/",
              "image":"images/hidden.webp",
              "order":1, "enabled":false
            }
          ]
        }
    """.trimIndent()

    @Test
    fun readsPersianCatalogAndExcludesDisabledEntries() {
        val parsed = TravelWebsiteCatalogParser.parse(validCatalog)
        assertEquals("برنامه‌ریزی سفر", parsed.categories.single().title)
        assertEquals(1, parsed.websites.size)
        assertEquals("rome2rio", parsed.websites.single().id)
    }

    @Test
    fun rejectsInsecureLinks() {
        val insecure = validCatalog.replace("https://www.rome2rio.com/", "http://www.rome2rio.com/")
        assertThrows(IllegalArgumentException::class.java) {
            TravelWebsiteCatalogParser.parse(insecure)
        }
    }

    @Test
    fun rejectsUnknownCategories() {
        val malformed = validCatalog.replace("\"category_id\":\"planning\"", "\"category_id\":\"invalid\"")
        assertThrows(IllegalArgumentException::class.java) {
            TravelWebsiteCatalogParser.parse(malformed)
        }
    }

    @Test
    fun rejectsUnsupportedSchema() {
        val malformed = validCatalog.replace("\"schema_version\": 1", "\"schema_version\": 2")
        assertThrows(IllegalArgumentException::class.java) {
            TravelWebsiteCatalogParser.parse(malformed)
        }
    }
}
