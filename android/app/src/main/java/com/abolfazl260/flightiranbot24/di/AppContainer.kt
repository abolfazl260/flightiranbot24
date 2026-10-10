package com.abolfazl260.flightiranbot24.di

import android.content.Context
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.abolfazl260.flightiranbot24.data.LocalHomeRepository
import com.abolfazl260.flightiranbot24.data.airports.RoomAirportCacheRepository
import com.abolfazl260.flightiranbot24.data.airports.TravelCacheDatabase
import com.abolfazl260.flightiranbot24.data.network.PublicHttpClientFactory
import com.abolfazl260.flightiranbot24.data.settings.DataStoreTravelerPreferencesRepository
import com.abolfazl260.flightiranbot24.data.settings.travelerPreferencesStore
import com.abolfazl260.flightiranbot24.domain.HomeRepository
import com.abolfazl260.flightiranbot24.presentation.home.HomeViewModel

/**
 * Explicit composition root, keeping dependency creation out of Composables.
 * Offline services are lazy and don't interrupt the existing Java Activities.
 * The versioned API has not been implemented: no client is constructed or
 * invoked until a verified URL is provided by AND-004 and API-001.
 */
internal class AppContainer(
    context: Context,
    val homeRepository: HomeRepository = LocalHomeRepository(),
) {
    private val application = context.applicationContext

    val travelerPreferencesRepository by lazy {
        DataStoreTravelerPreferencesRepository(application.travelerPreferencesStore)
    }

    val airportCacheRepository by lazy {
        RoomAirportCacheRepository(TravelCacheDatabase.getInstance(application))
    }

    fun publicApi(baseUrl: String) = PublicHttpClientFactory.create(baseUrl)

    val homeViewModelFactory: ViewModelProvider.Factory = viewModelFactory {
        initializer { HomeViewModel(homeRepository) }
    }
}
