package com.abolfazl260.flightiranbot24.presentation.fids

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.abolfazl260.flightiranbot24.data.fids.FlightDirection
import com.abolfazl260.flightiranbot24.data.fids.IranFidsBoard
import com.abolfazl260.flightiranbot24.data.fids.IranFidsRepository
import com.abolfazl260.flightiranbot24.data.fids.IranFidsResult
import com.abolfazl260.flightiranbot24.data.fids.iranFidsAirports
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

internal sealed interface IranFidsUiState {
    data object Loading : IranFidsUiState
    data object Unavailable : IranFidsUiState
    data class Ready(val board: IranFidsBoard) : IranFidsUiState
}

internal class IranFidsViewModel(private val repository: IranFidsRepository) : ViewModel() {
    private val mutable = MutableStateFlow<IranFidsUiState>(IranFidsUiState.Loading)
    val state = mutable.asStateFlow()
    private val airport = MutableStateFlow("THR")
    val selectedAirport = airport.asStateFlow()
    private val direction = MutableStateFlow(FlightDirection.DEPARTURES)
    val selectedDirection = direction.asStateFlow()
    private var request: Job? = null

    init { refresh() }

    fun selectAirport(code: String) {
        if (iranFidsAirports.none { it.code == code } || airport.value == code) return
        airport.value = code
        refresh()
    }

    fun selectDirection(value: FlightDirection) {
        if (direction.value == value) return
        direction.value = value
        refresh()
    }

    fun refresh() {
        request?.cancel()
        val selected = airport.value
        val selectedDirection = direction.value
        mutable.value = IranFidsUiState.Loading
        request = viewModelScope.launch {
            try {
                mutable.value = when (val result =
                    withContext(Dispatchers.IO) { repository.load(selected, selectedDirection) }) {
                    is IranFidsResult.Ready -> IranFidsUiState.Ready(result.board)
                    IranFidsResult.Unavailable -> IranFidsUiState.Unavailable
                }
            } catch (cancel: CancellationException) {
                throw cancel
            } catch (_: Exception) {
                mutable.value = IranFidsUiState.Unavailable
            }
        }
    }
}
