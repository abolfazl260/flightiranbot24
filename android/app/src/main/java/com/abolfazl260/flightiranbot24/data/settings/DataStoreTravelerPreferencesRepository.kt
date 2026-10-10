package com.abolfazl260.flightiranbot24.data.settings

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.abolfazl260.flightiranbot24.domain.settings.TravelerPreferences
import com.abolfazl260.flightiranbot24.domain.settings.TravelerPreferencesRepository
import java.io.IOException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map

internal val Context.travelerPreferencesStore: DataStore<Preferences> by preferencesDataStore(
    name = "traveler_preferences"
)

internal class DataStoreTravelerPreferencesRepository(
    private val dataStore: DataStore<Preferences>,
) : TravelerPreferencesRepository {
    private companion object {
        // Historical Android versions stored a language selection; it no longer controls UI.
        val LEGACY_LANGUAGE = stringPreferencesKey("language")
        val PASSPORT = stringPreferencesKey("default_passport_country")
        val COUNTRY_CODE = Regex("[A-Z]{2}")
    }

    override val preferences: Flow<TravelerPreferences> = dataStore.data
        .catch { failure ->
            if (failure is IOException) emit(emptyPreferences())
            else throw failure
        }
        .map { entry ->
            val country = entry[PASSPORT]
                ?.takeIf { COUNTRY_CODE.matches(it) } ?: "IR"
            TravelerPreferences(country)
        }

    override suspend fun setDefaultPassportCountry(countryCode: String) {
        require(COUNTRY_CODE.matches(countryCode)) { "Expected ISO-3166 alpha-2 country" }
        dataStore.edit {
            it.remove(LEGACY_LANGUAGE)
            it[PASSPORT] = countryCode
        }
    }
}
