package com.abolfazl260.flightiranbot24.presentation.tickets

import com.abolfazl260.flightiranbot24.data.tickets.TicketHistoryRepository
import com.abolfazl260.flightiranbot24.domain.network.*
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TicketHistoryViewModelTest {
    @Test fun loadingErrorRetryAndClosingIgnorePendingResults() = runTest {
        val dispatcher=StandardTestDispatcher(testScheduler);Dispatchers.setMain(dispatcher)
        try {
            var failed=true
            val api=object:PublicJsonRepository<JsonObject>{
                override suspend fun fetch(relativePath:String):NetworkResult<JsonObject> {
                    if(failed)return NetworkResult.ConnectionFailure
                    return NetworkResult.Success(javaClass.getResourceAsStream("/ticket-history-v1.json")!!.bufferedReader().use { JsonParser.parseReader(it).asJsonObject })
                }
            }
            val model=TicketHistoryViewModel(TicketHistoryRepository(api),dispatcher)
            model.open("A","B");assertSame(HistoryUiState.Loading,model.state.value)
            advanceUntilIdle();assertSame(HistoryUiState.Error,model.state.value)
            failed=false;model.retry();advanceUntilIdle();assertTrue(model.state.value is HistoryUiState.Ready)
            model.open("A","B");model.close();advanceUntilIdle()
            assertSame(HistoryUiState.Loading,model.state.value)
        } finally {Dispatchers.resetMain()}
    }
}
