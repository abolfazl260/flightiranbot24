package com.abolfazl260.flightiranbot24.presentation.tickets

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.abolfazl260.flightiranbot24.data.tickets.TicketPriceSnapshot
import com.abolfazl260.flightiranbot24.data.tickets.TicketPricesRepository
import com.abolfazl260.flightiranbot24.data.tickets.TicketPricesResult
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

internal sealed interface TicketPricesUiState {
    data object Loading : TicketPricesUiState
    data object Unconfigured : TicketPricesUiState
    data object Error : TicketPricesUiState
    data class Ready(val snapshot: TicketPriceSnapshot) : TicketPricesUiState
}
internal class TicketPricesViewModel(private val repository: TicketPricesRepository) : ViewModel() {
    private val mutable = MutableStateFlow<TicketPricesUiState>(TicketPricesUiState.Loading)
    val state: StateFlow<TicketPricesUiState> = mutable.asStateFlow()
    init { refresh() }

    fun refresh() {
        mutable.value = TicketPricesUiState.Loading
        viewModelScope.launch {
            try {
                mutable.value = when (val result = withContext(Dispatchers.IO) { repository.load() }) {
                    is TicketPricesResult.Ready -> TicketPricesUiState.Ready(result.value)
                    TicketPricesResult.Unconfigured -> TicketPricesUiState.Unconfigured
                    TicketPricesResult.Failed -> TicketPricesUiState.Error
                }
            } catch (cancel: CancellationException) {
                throw cancel
            } catch (_: Exception) {
                mutable.value = TicketPricesUiState.Error
            }
        }
    }
}
