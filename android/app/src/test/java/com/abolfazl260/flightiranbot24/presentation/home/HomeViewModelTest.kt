package com.abolfazl260.flightiranbot24.presentation.home

import com.abolfazl260.flightiranbot24.data.LocalHomeRepository
import com.abolfazl260.flightiranbot24.domain.HomeRepository
import com.abolfazl260.flightiranbot24.domain.HomeSections
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {
    private class FakeHomeRepository(
        var fail: Boolean = false,
        val valid: HomeSections,
    ) : HomeRepository {
        var requests = 0

        override suspend fun loadHomeSections(): HomeSections {
            requests += 1
            if (fail) {
                throw IllegalStateException("deliberate repository failure")
            }
            return valid
        }
    }

    @Test
    fun successfulRepositoryCreatesReadyStateWithoutContext() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        Dispatchers.setMain(dispatcher)
        try {
            val expected = LocalHomeRepository().loadHomeSections()
            val repository = FakeHomeRepository(valid = expected)
            val model = HomeViewModel(repository, dispatcher)
            assertSame(HomeUiState.Loading, model.state.value)
            advanceUntilIdle()
            assertEquals(HomeUiState.Ready(expected), model.state.value)
            assertEquals(1, repository.requests)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun repositoryFailureExposesRecoverableErrorThenRetry() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        Dispatchers.setMain(dispatcher)
        try {
            val repository = FakeHomeRepository(
                fail = true, valid = LocalHomeRepository().loadHomeSections()
            )
            val model = HomeViewModel(repository, dispatcher)
            advanceUntilIdle()
            assertSame(HomeUiState.Error, model.state.value)
            assertEquals(1, repository.requests)
            repository.fail = false
            model.refresh()
            assertSame(HomeUiState.Loading, model.state.value)
            advanceUntilIdle()
            assertTrue(model.state.value is HomeUiState.Ready)
            assertEquals(2, repository.requests)
        } finally {
            Dispatchers.resetMain()
        }
    }

    @Test
    fun repeatedRefreshDoesNotProduceDuplicateNavigationEntries() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        Dispatchers.setMain(dispatcher)
        try {
            val repository = FakeHomeRepository(
                valid = LocalHomeRepository().loadHomeSections()
            )
            val model = HomeViewModel(repository, dispatcher)
            advanceUntilIdle()
            repeat(3) {
                model.refresh()
                advanceUntilIdle()
            }
            val ready = model.state.value as HomeUiState.Ready
            val all = ready.sections.offline + ready.sections.online
            assertEquals(all.size, all.distinct().size)
            assertEquals(4, repository.requests)
        } finally {
            Dispatchers.resetMain()
        }
    }
}
