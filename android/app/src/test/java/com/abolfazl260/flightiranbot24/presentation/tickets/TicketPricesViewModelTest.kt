package com.abolfazl260.flightiranbot24.presentation.tickets

import com.abolfazl260.flightiranbot24.data.tickets.TicketPricesRepository
import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.time.OffsetDateTime
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TicketPricesViewModelTest {
    @Test fun refreshFailureKeepsLastRecordedSnapshotAndRetryRecovers() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        Dispatchers.setMain(dispatcher)
        try {
            var failed = false
            val api = object : PublicJsonRepository<JsonObject> {
                override suspend fun fetch(relativePath: String): NetworkResult<JsonObject> {
                    if (failed) return NetworkResult.ConnectionFailure
                    return NetworkResult.Success(JsonParser.parseString("""
                        {"currency":"TOMAN","observed_at":"${OffsetDateTime.now()}","stale":false,
                         "routes":[{"origin":"A","destinations":[
                         {"name":"B","price_toman":80,"average_price_toman":100,"average_sample_count":3}]}]}
                    """).asJsonObject)
                }
            }
            val model = TicketPricesViewModel(TicketPricesRepository(api),dispatcher)
            assertSame(TicketPricesUiState.Loading,model.state.value)
            advanceUntilIdle()
            val ready = model.state.value as TicketPricesUiState.Ready
            assertFalse(ready.snapshot.stale)
            failed = true; model.refresh()
            assertTrue((model.state.value as TicketPricesUiState.Ready).refreshing)
            advanceUntilIdle()
            val error = model.state.value as TicketPricesUiState.Ready
            assertTrue(error.refreshError); assertTrue(error.snapshot.stale)
            assertEquals(ready.snapshot.origins,error.snapshot.origins)
            failed = false; model.refresh(); advanceUntilIdle()
            assertFalse((model.state.value as TicketPricesUiState.Ready).refreshError)
        } finally { Dispatchers.resetMain() }
    }
}
