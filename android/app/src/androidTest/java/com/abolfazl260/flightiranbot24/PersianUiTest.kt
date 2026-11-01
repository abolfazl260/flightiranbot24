package com.abolfazl260.flightiranbot24

import androidx.compose.ui.test.assertHasClickAction
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** UI assertions run on an emulator even when its system language is English. */
@RunWith(AndroidJUnit4::class)
class PersianUiTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    @Test
    fun homeUsesPersianLocaleAndRtlNavigation() {
        rule.activityRule.scenario.onActivity {
            val appLocale = it.resources.configuration.locales[0]
            assertEquals("fa", appLocale.language)
        }
        rule.onNodeWithText("سفر، ساده‌تر از همیشه").assertExists()
        rule.onNodeWithContentDescription("خانه").assertExists()
        rule.onNodeWithContentDescription("قیمت بلیت").assertHasClickAction()
        // Airports remain available from the home card, not from bottom nav.
        rule.onNodeWithText("فرودگاه‌ها").assertDoesNotExist()
        rule.onNodeWithContentDescription("راهنمای فرودگاه‌ها").assertHasClickAction()
        rule.onNodeWithContentDescription("چک‌لیست").assertHasClickAction()
        // The airport feature is disabled: tapping the card opens Services
        // without launching the former AirportDirectoryActivity.
        rule.onNodeWithContentDescription("راهنمای فرودگاه‌ها").performClick()
        rule.onNodeWithText("خدمات بیشتر").assertExists()
        rule.onNodeWithText("اطلاعات فرودگاه‌ها").assertDoesNotExist()
        rule.onNodeWithContentDescription("خانه").performClick()
        rule.onNodeWithText("سفر، ساده‌تر از همیشه").assertExists()
        rule.onNodeWithContentDescription("خدمات").performClick()
        rule.onNodeWithText("خدمات بیشتر").assertExists()
    }
}
