package com.abolfazl260.flightiranbot24

import androidx.compose.ui.test.assertExists
import androidx.compose.ui.test.assertHasClickAction
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
        rule.onNodeWithText("دستیار سفر Flight Iran Bot 24").assertExists()
        rule.onNodeWithText("خانه").assertExists()
        rule.onNodeWithText("فهرست فرودگاه‌ها · آفلاین").assertHasClickAction()
        rule.onNodeWithText("چک‌لیست سفر من · آفلاین").assertHasClickAction()
        rule.onNodeWithText("خدمات").performClick()
        rule.onNodeWithText("خدمات آنلاین سفر").assertExists()
    }
}
