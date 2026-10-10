package com.abolfazl260.flightiranbot24.di

import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.abolfazl260.flightiranbot24.data.LocalHomeRepository
import com.abolfazl260.flightiranbot24.domain.HomeRepository
import com.abolfazl260.flightiranbot24.presentation.home.HomeViewModel

/**
 * Small explicit composition root. Avoids introducing Hilt/KSP until the
 * Android app has a genuinely large graph of API clients and repositories.
 * Tests can inject a fake HomeRepository without starting an Activity.
 */
internal class AppContainer(
    val homeRepository: HomeRepository = LocalHomeRepository(),
) {
    val homeViewModelFactory: ViewModelProvider.Factory = viewModelFactory {
        initializer { HomeViewModel(homeRepository) }
    }
}
