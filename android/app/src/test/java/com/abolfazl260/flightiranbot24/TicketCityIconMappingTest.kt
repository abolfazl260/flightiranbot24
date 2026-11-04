package com.abolfazl260.flightiranbot24

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class TicketCityIconMappingTest {
    @Test
    fun mapsFortyCitiesToStableResourceNames() {
        val expected = mapOf(
            "مشهد" to "price_city_mashhad",
            "استانبول" to "price_city_istanbul",
            "نجف" to "price_city_najaf",
            "شیراز" to "price_city_shiraz",
            "اهواز" to "price_city_ahvaz",
            "کیش" to "price_city_kish",
            "تبریز" to "price_city_tabriz",
            "کرمان" to "price_city_kerman",
            "ایروان" to "price_city_yerevan",
            "بندرعباس" to "price_city_bandarabbas",
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
            "تهران" to "price_city_tehran",
            "اصفهان" to "price_city_isfahan",
            "رشت" to "price_city_rasht",
            "همدان" to "price_city_hamedan",
            "قم" to "price_city_qom",
            "گرگان" to "price_city_gorgan",
            "دبی" to "price_city_dubai",
            "دوحه" to "price_city_doha",
            "آنکارا" to "price_city_ankara",
            "آنتالیا" to "price_city_antalya",
            "سنندج" to "price_city_sanandaj",
            "ساری" to "price_city_sari",
            "اردبیل" to "price_city_ardabil",
            "کاشان" to "price_city_kashan",
            "خرم‌آباد" to "price_city_khorramabad",
            "زنجان" to "price_city_zanjan",
            "اراک" to "price_city_arak",
            "یاسوج" to "price_city_yasuj",
            "چابهار" to "price_city_chabahar",
            "بندر انزلی" to "price_city_bandaranzali",
        )
        expected.forEach { (city, resourceName) ->
            assertEquals(city, resourceName, fareCityIconName(city))
        }
    }

    @Test
    fun supportsWhitespaceAndArabicLetterVariants() {
        assertEquals("price_city_moscow_sheremetyevo", fareCityIconName("مسکو (شرمتیوو)"))
        assertEquals("price_city_kermanshah", fareCityIconName("كرمانشاه"))
        assertEquals("price_city_khorramabad", fareCityIconName("خرم آباد"))
        assertEquals("price_city_bandaranzali", fareCityIconName("بندرانزلی"))
    }

    @Test
    fun leavesCitiesWithoutDedicatedImagesUnchanged() {
        assertNull(fareCityIconName("قزوین"))
        assertEquals("price_city_tehran", fareCityIconName("تهران"))
    }
}
