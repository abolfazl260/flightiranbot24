package com.abolfazl260.flightiranbot24.domain.settings

import kotlinx.coroutines.flow.Flow

/** Only non-sensitive traveler defaults are stored; the Android UI is always Persian. */
internal data class TravelerPreferences(
    val defaultPassportCountry: String = "IR",
)

internal interface TravelerPreferencesRepository {
    val preferences: Flow<TravelerPreferences>
    suspend fun setDefaultPassportCountry(countryCode: String)
}
