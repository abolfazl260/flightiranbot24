package com.abolfazl260.flightiranbot24

import androidx.compose.ui.test.assertHasClickAction
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onFirst
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.unit.Density
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.abolfazl260.flightiranbot24.data.tickets.TicketFare
import com.abolfazl260.flightiranbot24.data.tickets.TicketHistoryRepository
import com.abolfazl260.flightiranbot24.data.tickets.TicketOrigin
import com.abolfazl260.flightiranbot24.data.tickets.TicketPriceSnapshot
import com.abolfazl260.flightiranbot24.domain.network.NetworkResult
import com.abolfazl260.flightiranbot24.domain.network.PublicJsonRepository
import com.abolfazl260.flightiranbot24.presentation.tickets.TicketPricesUiState
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import com.google.gson.JsonObject
import java.net.URLEncoder
import java.util.concurrent.CopyOnWriteArrayList
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TicketPricesUiTest {
    @get:Rule val rule = createComposeRule()

    @Test fun sharedHeaderCardsAndThreeDestinationFiltersStayConsistent() {
        val fares = listOf(
            TicketFare("کیش", 21_990_000, 38_380_800, -42.7, 5, 38_380_800.0),
            TicketFare("تبریز", 25_990_000, null, null, 0, null),
        )
        val state = TicketPricesUiState.Ready(
            TicketPriceSnapshot(
                origins = listOf(TicketOrigin("تهران", fares)),
                observedAt = "2026-11-15T04:00:00Z",
                stale = false,
            ),
        )
        val requestedPaths = CopyOnWriteArrayList<String>()
        val noNetwork = object : PublicJsonRepository<JsonObject> {
            override suspend fun fetch(relativePath: String): NetworkResult<JsonObject> {
                requestedPaths.add(relativePath)
                return NetworkResult.ConnectionFailure
            }
        }

        rule.setContent {
            TravelTheme {
                TicketPricesScreen(
                    state = state,
                    onBack = {},
                    onRefresh = {},
                    onSupport = {},
                    allowSupport = false,
                    historyRepository = TicketHistoryRepository(noNetwork),
                )
            }
        }

        rule.onNodeWithText("قیمت بلیت از تهران").assertExists()
        rule.onNodeWithText("۲ مقصد").assertExists()
        rule.onNodeWithText("۲۴ آبان ۱۴۰۵، ساعت ۰۷:۳۰").assertExists()
        rule.onAllNodesWithText("کمترین قیمت ثبت‌شده").onFirst().performScrollTo().assertExists()
        rule.onAllNodesWithText("میانگین قیمت").onFirst().assertExists()
        rule.onAllNodesWithText("مشاهده نمودار ←").onFirst().assertHasClickAction()
        rule.onNodeWithText("از تهران به کیش").assertDoesNotExist()
        rule.onNodeWithText("زمان ثبت").assertDoesNotExist()
        rule.onNodeWithText("نمودار قیمت این مسیر").assertDoesNotExist()
        rule.onNodeWithText("بدون مقایسه").assertDoesNotExist()

        rule.onNodeWithText("بیشترین کاهش").performScrollTo().performClick()
        rule.onNodeWithText("کیش").performScrollTo().assertExists()
        rule.onNodeWithText("تبریز").assertDoesNotExist()

        rule.onNodeWithText("همه مقاصد").performScrollTo().performClick()
        rule.onNodeWithText("تبریز").performScrollTo().assertExists()
        rule.onNodeWithText("در دسترس نیست").assertExists()

        rule.onNodeWithText("کیش").performScrollTo()
        rule.onAllNodesWithText("مشاهده نمودار ←").onFirst().performClick()
        rule.waitUntil(timeoutMillis = 5_000) { requestedPaths.isNotEmpty() }
        val expectedPath = "api/v1/tickets/history?origin=${URLEncoder.encode("تهران", "UTF-8")}" +
            "&destination=${URLEncoder.encode("کیش", "UTF-8")}"
        assertEquals(expectedPath, requestedPaths.single())
    }

    @Test fun sharedHeaderAndFareValuesRemainReadableAtLargeFontScale() {
        val state = TicketPricesUiState.Ready(
            TicketPriceSnapshot(
                origins = listOf(
                    TicketOrigin(
                        "تهران",
                        listOf(TicketFare("کیش", 21_990_000, 38_380_800, -42.7, 5, 38_380_800.0)),
                    ),
                ),
                observedAt = "2026-11-15T04:00:00Z",
                stale = false,
            ),
        )

        rule.setContent {
            val baseDensity = LocalDensity.current
            CompositionLocalProvider(
                LocalDensity provides Density(baseDensity.density, fontScale = 2f),
            ) {
                TravelTheme {
                    TicketPricesScreen(
                        state = state,
                        onBack = {},
                        onRefresh = {},
                        onSupport = {},
                        allowSupport = false,
                    )
                }
            }
        }

        rule.onNodeWithText("قیمت بلیت از تهران").assertExists()
        rule.onNodeWithText("۲ مقصد").assertExists()
        rule.onNodeWithText("آخرین به‌روزرسانی: ۲۴ آبان ۱۴۰۵، ساعت ۰۷:۳۰").assertExists()
        rule.onNodeWithText("کمترین قیمت ثبت‌شده").performScrollTo().assertExists()
        rule.onNodeWithText("میانگین قیمت").assertExists()
        rule.onNodeWithText("تومان").assertExists()
    }

}
