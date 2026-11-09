package com.abolfazl260.flightiranbot24.presentation.tickets

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.abolfazl260.flightiranbot24.data.tickets.TicketPriceSnapshot
import com.abolfazl260.flightiranbot24.data.tickets.TicketPricesRepository
import com.abolfazl260.flightiranbot24.data.tickets.TicketPricesResult
import kotlinx.coroutines.CoroutineDispatcher
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
    data class Ready(val snapshot: TicketPriceSnapshot, val refreshing: Boolean = false,
        val refreshError: Boolean = false) : TicketPricesUiState
}
internal class TicketPricesViewModel(
    private val repository: TicketPricesRepository,
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO,
) : ViewModel() {
    private val mutable = MutableStateFlow<TicketPricesUiState>(TicketPricesUiState.Loading)
    val state: StateFlow<TicketPricesUiState> = mutable.asStateFlow()
    private var requestId = 0
    init { refresh() }

    fun refresh() {
        val request = ++requestId
        val previous = mutable.value as? TicketPricesUiState.Ready
        mutable.value = previous?.copy(refreshing = true, refreshError = false)
            ?: TicketPricesUiState.Loading
        viewModelScope.launch {
            fun failure(): TicketPricesUiState = previous?.let {
                TicketPricesUiState.Ready(it.snapshot.copy(stale = true), refreshError = true)
            } ?: TicketPricesUiState.Error
            try {
                val result = withContext(dispatcher) { repository.load() }
                if (request != requestId) return@launch
                mutable.value = when (result) {
                    is TicketPricesResult.Ready -> TicketPricesUiState.Ready(result.value)
                    TicketPricesResult.Unconfigured -> previous?.let { failure() }
                        ?: TicketPricesUiState.Unconfigured
                    TicketPricesResult.Failed -> failure()
                }
            } catch (cancel: CancellationException) {
                throw cancel
            } catch (_: Exception) {
                if (request == requestId) mutable.value = failure()
            }
        }
    }
}
