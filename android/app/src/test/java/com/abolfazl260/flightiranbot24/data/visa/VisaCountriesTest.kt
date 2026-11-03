package com.abolfazl260.flightiranbot24.data.visa

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class VisaCountriesTest {
    @Test fun commonCountriesArePersianAndFlagsAreDerivedFromValidCodes() {
        assertEquals("ترکیه", VisaCountries.name("TR"))
        assertEquals("ایران", VisaCountries.name("IR"))
        assertTrue(VisaCountries.flag("IR").isNotBlank())
        assertEquals("🌐", VisaCountries.flag("IRAN"))
    }

    @Test fun searchesPersianArabicOrthographyAndEnglishCountryNames() {
        assertTrue(VisaCountries.matches("TR", "Turkey", "تركيه"))
        assertTrue(VisaCountries.matches("TR", "Turkey", "ترکیه"))
        assertTrue(VisaCountries.matches("TR", "Turkey", "TURKEY"))
        assertTrue(VisaCountries.matches("TR", "Turkey", "tr"))
        assertFalse(VisaCountries.matches("TR", "Turkey", "مالزی"))
    }
}
