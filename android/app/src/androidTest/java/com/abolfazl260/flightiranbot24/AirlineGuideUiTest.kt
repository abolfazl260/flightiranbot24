package com.abolfazl260.flightiranbot24

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertHasClickAction
import androidx.compose.ui.test.hasScrollToIndexAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.performTextInput
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.abolfazl260.flightiranbot24.presentation.theme.TravelTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Deterministic RTL screens; no live network, publication changes or personal data. */
@RunWith(AndroidJUnit4::class)
class AirlineGuideUiTest {
    @get:Rule val rule = createComposeRule()
    private val context: Context get() = ApplicationProvider.getApplicationContext()
    private fun bundled(path: String) = context.assets.open(path).bufferedReader().use { it.readText() }

    // Airline sections are rendered in a LazyColumn. Off-screen rows do not
    // exist in the semantics tree until the list itself scrolls to them.
    private fun scrollToSection(text: String) {
        rule.onNode(hasScrollToIndexAction()).performScrollToNode(hasText(text))
    }

    @Test fun directorySearchAndServiceNavigationAreNativeClickableAndPersian() {
        val index = AirlineContentParser.index(bundled("airline-index.v1.json"))
        val page = AirlineContentParser.detail(bundled("details/emirates.v1.json"), "emirates")
        rule.setContent {
            var selected by remember { mutableStateOf<String?>(null) }
            var section by remember { mutableStateOf<String?>(null) }
            TravelTheme {
                AirlineGuideScreen(index, if (selected == "emirates") page else null,
                    selected, section, loading = false, error = false, offline = true,
                    onSelect = { selected = it }, onSection = { section = it },
                    onBack = { if (section != null) section = null else selected = null },
                    onRetry = {}, onLink = {}, onAirport = {}, onShare = {},
                    onHome = {}, onServices = {}, onPrices = {}, onChecklist = {})
            }
        }
        rule.onNodeWithText("جست‌وجوی نام، نام پیشین یا کد ایرلاین").performTextInput("EK")
        rule.onNodeWithText("ایران‌ایر").assertDoesNotExist()
        rule.onNodeWithText("امارات", useUnmergedTree = true).performScrollTo().performClick()
        scrollToSection("ناوگان هواپیما")
        rule.onNodeWithText("ناوگان هواپیما").assertHasClickAction()
        rule.onNodeWithText("ناوگان هواپیما").performClick()
        scrollToSection("Airbus A380-800")
        rule.onAllNodesWithText("Airbus A380-800").onFirst().assertExists()
        scrollToSection("بازگشت")
        rule.onNodeWithText("بازگشت").performClick()
        scrollToSection("بار مجاز و اقلام خاص")
        rule.onNodeWithText("بار مجاز و اقلام خاص").assertHasClickAction()
    }

    @Test fun unpublishedStateHasClearPersianMessage() {
        rule.setContent {
            TravelTheme {
                AirlineGuideScreen(null, null, "emirates", null,
                    loading = false, error = false, offline = false,
                    onSelect = {}, onSection = {}, onBack = {}, onRetry = {},
                    onLink = {}, onAirport = {}, onShare = {},
                    onHome = {}, onServices = {}, onPrices = {}, onChecklist = {})
            }
        }
        rule.onNodeWithText("این راهنما هنوز منتشر نشده یا فعلاً در دسترس نیست.").assertExists()
    }
}
