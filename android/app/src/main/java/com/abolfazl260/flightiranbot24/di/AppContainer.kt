package com.abolfazl260.flightiranbot24.di

import android.content.Context
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.abolfazl260.flightiranbot24.data.LocalHomeRepository
import com.abolfazl260.flightiranbot24.data.tickets.TicketPricesRepository
import com.abolfazl260.flightiranbot24.presentation.tickets.TicketPricesViewModel
import com.abolfazl260.flightiranbot24.data.airports.RoomAirportCacheRepository
import com.abolfazl260.flightiranbot24.data.airports.TravelCacheDatabase
import com.abolfazl260.flightiranbot24.data.settings.DataStoreTravelerPreferencesRepository
import com.abolfazl260.flightiranbot24.data.settings.travelerPreferencesStore
import com.abolfazl260.flightiranbot24.domain.HomeRepository
import com.abolfazl260.flightiranbot24.presentation.home.HomeViewModel

/**
 * Explicit composition root, keeping dependency creation out of Composables.
 * Local services are lazy and preserve existing Java Activities.
 * The versioned public ticket API is configured with a deployed HTTPS origin
 * at build time; no credentials are embedded in the Android application.
 */
internal class AppContainer(
    context: Context,
    val homeRepository: HomeRepository = LocalHomeRepository(),
) {
    private val application = context.applicationContext
    val environment = EnvironmentSettings.fromBuild()

    val travelerPreferencesRepository by lazy {
        DataStoreTravelerPreferencesRepository(application.travelerPreferencesStore)
    }

    val airportCacheRepository by lazy {
        RoomAirportCacheRepository(TravelCacheDatabase.getInstance(application))
    }

    // A caller cannot override environment origin or select production manually.
    fun publicApi() = environment.publicApi()

    val ticketPricesViewModelFactory: ViewModelProvider.Factory = viewModelFactory {
        initializer { TicketPricesViewModel(TicketPricesRepository(publicApi())) }
    }

    val homeViewModelFactory: ViewModelProvider.Factory = viewModelFactory {
        initializer { HomeViewModel(homeRepository) }
    }
}
