package com.abolfazl260.flightiranbot24.domain.settings

import kotlinx.coroutines.flow.Flow

/**
 * Only non-sensitive display preferences are stored in DataStore. No
 * access/refresh token, user password, passport number or bot credential.
 */
internal data class TravelerPreferences(
    val language: String = "fa",
    val defaultPassportCountry: String = "IR",
)

internal interface TravelerPreferencesRepository {
    val preferences: Flow<TravelerPreferences>
    suspend fun setLanguage(language: String)
    suspend fun setDefaultPassportCountry(countryCode: String)
}
