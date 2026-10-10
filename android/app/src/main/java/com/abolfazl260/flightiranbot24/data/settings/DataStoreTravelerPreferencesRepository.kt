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

// A single DataStore instance is maintained per file/process by this delegate.
internal val Context.travelerPreferencesStore: DataStore<Preferences> by preferencesDataStore(
    name = "traveler_preferences"
)

internal class DataStoreTravelerPreferencesRepository(
    private val dataStore: DataStore<Preferences>,
) : TravelerPreferencesRepository {
    private companion object {
        val LANGUAGE = stringPreferencesKey("language")
        val PASSPORT = stringPreferencesKey("default_passport_country")
        val LANGUAGES = setOf("fa", "en", "ar")
        val COUNTRY_CODE = Regex("[A-Z]{2}")
    }

    override val preferences: Flow<TravelerPreferences> = dataStore.data
        .catch { failure ->
            if (failure is IOException) emit(emptyPreferences())
            else throw failure
        }
        .map { entry ->
            val language = entry[LANGUAGE]?.takeIf { it in LANGUAGES } ?: "fa"
            val country = entry[PASSPORT]
                ?.takeIf { COUNTRY_CODE.matches(it) } ?: "IR"
            TravelerPreferences(language, country)
        }

    override suspend fun setLanguage(language: String) {
        require(language in LANGUAGES) { "Unsupported interface language" }
        dataStore.edit { it[LANGUAGE] = language }
    }

    override suspend fun setDefaultPassportCountry(countryCode: String) {
        require(COUNTRY_CODE.matches(countryCode)) { "Expected ISO-3166 alpha-2 country" }
        dataStore.edit { it[PASSPORT] = countryCode }
    }
}
