package com.abolfazl260.flightiranbot24.presentation.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.abolfazl260.flightiranbot24.domain.HomeRepository
import com.abolfazl260.flightiranbot24.domain.HomeSections
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** No Android resource IDs, Activity or Context references in ViewModel state. */
internal sealed interface HomeUiState {
    data object Loading : HomeUiState
    data class Ready(val sections: HomeSections) : HomeUiState
    data object Error : HomeUiState
}

internal class HomeViewModel(
    private val repository: HomeRepository,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.Default,
) : ViewModel() {
    private val mutableState = MutableStateFlow<HomeUiState>(HomeUiState.Loading)
    val state: StateFlow<HomeUiState> = mutableState.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            mutableState.value = HomeUiState.Loading
            try {
                val sections = withContext(ioDispatcher) {
                    repository.loadHomeSections()
                }
                mutableState.value = HomeUiState.Ready(sections)
            } catch (cancel: CancellationException) {
                // Cancellation on Activity disposal is not a loading error.
                throw cancel
            } catch (_: Exception) {
                mutableState.value = HomeUiState.Error
            }
        }
    }
}
