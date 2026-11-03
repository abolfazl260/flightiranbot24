package com.abolfazl260.flightiranbot24.presentation.visa

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.abolfazl260.flightiranbot24.data.visa.VisaFetch
import com.abolfazl260.flightiranbot24.data.visa.VisaFailure
import com.abolfazl260.flightiranbot24.data.visa.VisaRepository
import com.abolfazl260.flightiranbot24.data.visa.VisaRule
import com.abolfazl260.flightiranbot24.domain.settings.TravelerPreferencesRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

internal sealed interface VisaLoad<out T> {
    data object Loading : VisaLoad<Nothing>
    data object Idle : VisaLoad<Nothing>
    data class Ready<T>(val data: T) : VisaLoad<T>
    data class Error(val reason: VisaFailure) : VisaLoad<Nothing>
}

internal data class VisaGuideState(
    val passport: String = "IR",
    val catalog: VisaLoad<List<VisaRule>> = VisaLoad.Loading,
    val selectedDestination: String? = null,
    val detail: VisaLoad<VisaRule> = VisaLoad.Idle,
)

internal class VisaGuideViewModel(
    private val repository: VisaRepository,
    private val preferences: TravelerPreferencesRepository,
) : ViewModel() {
    private val mutable = MutableStateFlow(VisaGuideState())
    val state: StateFlow<VisaGuideState> = mutable.asStateFlow()
    private var listJob: Job? = null
    private var detailJob: Job? = null

    init {
        viewModelScope.launch {
            preferences.preferences.collectLatest { setting ->
                val passport = setting.defaultPassportCountry
                if (mutable.value.passport != passport || listJob == null) {
                    loadPassport(passport)
                }
            }
        }
    }

    fun choosePassport(code: String) {
        if (!Regex("[A-Z]{2}").matches(code) || code == mutable.value.passport) return
        // Invalidate the previous rule immediately, before the preference flow emits.
        detailJob?.cancel()
        listJob?.cancel()
        mutable.value = VisaGuideState(passport = code)
        viewModelScope.launch {
            try {
                preferences.setDefaultPassportCountry(code)
                loadPassport(code)
            } catch (cancel: CancellationException) {
                throw cancel
            } catch (_: Exception) {
                mutable.value = VisaGuideState(passport = code, catalog = VisaLoad.Error(VisaFailure.INVALID))
            }
        }
    }

    private fun loadPassport(passport: String) {
        listJob?.cancel()
        detailJob?.cancel()
        mutable.value = VisaGuideState(passport = passport)
        listJob = viewModelScope.launch {
            val result = fetch { repository.list(passport) }
            if (mutable.value.passport == passport) {
                mutable.value = mutable.value.copy(catalog = result)
            }
        }
    }

    fun retryCatalog() = loadPassport(mutable.value.passport)

    fun openDestination(destination: String) {
        if (!Regex("[A-Z]{2}").matches(destination) || destination == mutable.value.passport) return
        detailJob?.cancel()
        val passport = mutable.value.passport
        mutable.value = mutable.value.copy(
            selectedDestination = destination,
            detail = VisaLoad.Loading,
        )
        detailJob = viewModelScope.launch {
            val result = fetch { repository.detail(passport, destination) }
            if (mutable.value.passport == passport && mutable.value.selectedDestination == destination) {
                mutable.value = mutable.value.copy(detail = result)
            }
        }
    }

    fun retryDetail() {
        mutable.value.selectedDestination?.let(::openDestination)
    }

    fun backToCountries(): Boolean {
        if (mutable.value.selectedDestination == null) return false
        detailJob?.cancel()
        mutable.value = mutable.value.copy(selectedDestination = null, detail = VisaLoad.Idle)
        return true
    }

    private suspend fun <T> fetch(call: suspend () -> VisaFetch<T>): VisaLoad<T> {
        return try {
            when (val result = withContext(Dispatchers.IO) { call() }) {
                is VisaFetch.Ready -> VisaLoad.Ready(result.value)
                is VisaFetch.Error -> VisaLoad.Error(result.reason)
            }
        } catch (cancel: CancellationException) {
            throw cancel
        } catch (_: Exception) {
            VisaLoad.Error(VisaFailure.INVALID)
        }
    }
}
