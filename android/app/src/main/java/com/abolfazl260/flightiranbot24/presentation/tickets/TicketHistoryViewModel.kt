package com.abolfazl260.flightiranbot24.presentation.tickets

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.abolfazl260.flightiranbot24.data.tickets.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal sealed interface HistoryUiState {
    data object Loading : HistoryUiState
    data object Error : HistoryUiState
    data class Ready(val history: TicketHistory) : HistoryUiState
    data class Routes(val page: HistoryRoutes, val offset: Int) : HistoryUiState
}
internal class TicketHistoryViewModel(private val repository: TicketHistoryRepository,
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO) : ViewModel() {
    private val mutable = MutableStateFlow<HistoryUiState>(HistoryUiState.Loading)
    val state = mutable.asStateFlow()
    var route: Pair<String,String>? = null
        private set
    private var request = 0
    private var action: () -> Unit = { routes() }
    fun open(origin: String, destination: String) {
        route = origin to destination
        action = { open(origin,destination) }
        load { HistoryUiState.Ready(repository.load(origin,destination)) }
    }
    fun routes(offset: Int = 0) {
        action = { routes(offset) }
        load { HistoryUiState.Routes(repository.routes(offset),offset) }
    }
    fun retry() = action()
    fun close() { request++ }
    private fun load(block: suspend () -> HistoryUiState) {
        val id = ++request; mutable.value = HistoryUiState.Loading
        viewModelScope.launch {
            try {
                val value = withContext(dispatcher) { block() }
                if(id == request) mutable.value = value
            } catch(e: CancellationException) { throw e }
            catch(_: Exception) { if(id == request) mutable.value = HistoryUiState.Error }
        }
    }
}
