package com.abolfazl260.flightiranbot24.data.tickets

import com.google.gson.JsonParser
import org.junit.Assert.*
import org.junit.Test

class ExperiencesRepositoryTest {
    private fun fixture()=javaClass.getResourceAsStream("/experiences-public-v1.json")!!.bufferedReader().use {JsonParser.parseReader(it).asJsonObject}
    @Test fun sharedPublicFixtureKeepsRealVotesFullTextAndUnknownDates(){
        val page=ExperiencesRepository(null).parse(fixture())!!
        assertEquals(1,page.count);assertEquals(4.0,page.average!!,0.001);assertTrue(page.lowSample);assertFalse(page.comparison)
        assertEquals(listOf("airline:iran-air","airport:IKA"),page.items.single().targets)
        assertTrue(page.items.single().text.contains("<script>safe text</script>"));assertNull(page.items.single().travelDate)
        assertEquals(5,page.items.single().criteria["cleanliness"])
    }
    @Test fun absentAndMalformedRatingsNeverBecomeSyntheticStars(){
        val invalid=fixture();invalid.getAsJsonObject("stats").addProperty("rating_count",0)
        assertNull(ExperiencesRepository(null).parse(invalid))
        val bad=fixture();bad.getAsJsonArray("items")[0].asJsonObject.addProperty("rating",6)
        assertNull(ExperiencesRepository(null).parse(bad))
        val archive=fixture();archive.getAsJsonArray("items")[0].asJsonObject.addProperty("kind","archive")
        assertNull(ExperiencesRepository(null).parse(archive))
    }
}
