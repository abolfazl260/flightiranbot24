package com.abolfazl260.flightiranbot24

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class TicketCityIconMappingTest {
    @Test
    fun mapsSecondBatchCitiesToStableResourceNames() {
        val expected = mapOf(
            "زاهدان" to "price_city_zahedan",
            "ارومیه" to "price_city_urmia",
            "آبادان" to "price_city_abadan",
            "عسلویه" to "price_city_assaluyeh",
            "بوشهر" to "price_city_bushehr",
            "یزد" to "price_city_yazd",
            "کرمانشاه" to "price_city_kermanshah",
            "گوانجو" to "price_city_guangzhou",
            "مسکو(شرمتیوو)" to "price_city_moscow_sheremetyevo",
            "قشم" to "price_city_qeshm",
        )
        expected.forEach { (city, resourceName) ->
            assertEquals(city, resourceName, fareCityIconName(city))
        }
    }

    @Test
    fun supportsWhitespaceAndArabicLetterVariants() {
        assertEquals("price_city_moscow_sheremetyevo", fareCityIconName("مسکو (شرمتیوو)"))
        assertEquals("price_city_kermanshah", fareCityIconName("كرمانشاه"))
    }

    @Test
    fun leavesCitiesWithoutDedicatedImagesUnchanged() {
        assertNull(fareCityIconName("تهران"))
    }
}
