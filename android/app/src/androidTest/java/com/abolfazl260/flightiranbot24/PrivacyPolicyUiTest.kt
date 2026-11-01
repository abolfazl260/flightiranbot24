package com.abolfazl260.flightiranbot24

import androidx.compose.ui.test.assertHasClickAction
import androidx.compose.ui.test.assertExists
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** The privacy notice must be readable without opening GitHub or a WebView. */
@RunWith(AndroidJUnit4::class)
class PrivacyPolicyUiTest {
    @get:Rule val rule = createAndroidComposeRule<PrivacyPolicyActivity>()

    @Test
    fun privacyNoticeIsNativePersianAndContainsAllSections() {
        rule.onNodeWithText("حریم خصوصی").assertExists()
        rule.onNodeWithText("بازگشت").assertHasClickAction()
        rule.onNodeWithText("اطلاعات ذخیره‌شده در گوشی").assertExists()
        rule.onNodeWithText("ارتباط با اینترنت و سرویس‌های آنلاین").assertExists()
        rule.onNodeWithText("مجوزهای دستگاه").assertExists()
        rule.onNodeWithText("تلگرام و خدمات بیرونی").assertExists()
        rule.onNodeWithText("پاک‌کردن داده‌ها و ارتباط با پشتیبانی").assertExists()
    }
}
