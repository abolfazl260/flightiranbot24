package com.abolfazl260.flightiranbot24

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertHasClickAction
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
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
        rule.onNodeWithText("ناوگان هواپیما").performScrollTo().assertHasClickAction()
        rule.onNodeWithText("ناوگان هواپیما").performClick()
        rule.onNodeWithText("Airbus A350").performScrollTo().assertExists()
        rule.onNodeWithText("بازگشت").performScrollTo().performClick()
        rule.onNodeWithText("بار مجاز و اقلام خاص").performScrollTo().assertHasClickAction()
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
