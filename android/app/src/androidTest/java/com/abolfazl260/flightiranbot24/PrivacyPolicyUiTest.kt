package com.abolfazl260.flightiranbot24

import androidx.compose.ui.test.assertHasClickAction
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Privacy remains native and offline; expanded copy is available on demand. */
@RunWith(AndroidJUnit4::class)
class PrivacyPolicyUiTest {
    @get:Rule val rule = createAndroidComposeRule<PrivacyPolicyActivity>()

    @Test
    fun privacyOverviewShowsAllSectionsAndDataActions() {
        rule.onNodeWithText("حریم خصوصی").assertExists()
        rule.onNodeWithText("بازگشت").assertHasClickAction()
        rule.onNodeWithText("خلاصه حریم خصوصی").assertExists()
        rule.onNodeWithText("اطلاعات ذخیره‌شده در گوشی").assertExists()
        rule.onNodeWithText("ارتباط با اینترنت").assertExists()
        rule.onNodeWithText("دسترسی‌های برنامه").assertExists()
        rule.onNodeWithText("تلگرام و سرویس‌های خارجی").assertExists()
        rule.onNodeWithText("مدیریت و حذف اطلاعات").assertExists()
        rule.onNodeWithText("نگهداری و امنیت اطلاعات").assertExists()
        rule.onNodeWithText("تغییرات سیاست حریم خصوصی").assertExists()
        rule.onNodeWithText("آخرین بازبینی: ۱۲ آبان ۱۴۰۵").assertExists()
        rule.onNodeWithText("مدیریت و پاک‌کردن چک‌لیست").assertHasClickAction()
        rule.onNodeWithText("تنظیمات برنامه در اندروید").assertHasClickAction()
        rule.onNodeWithText("ارتباط با پشتیبانی").assertHasClickAction()
    }

    @Test
    fun privacySectionsExpandAndCollapseWithoutNavigatingAway() {
        val section = rule.onNodeWithTag("privacy-section-0")
        section.assertHasClickAction()
        rule.onNodeWithText(
            "برای استفاده از این قابلیت‌ها نیازی به ساخت حساب کاربری",
            substring = true,
        ).assertDoesNotExist()

        section.performClick()
        rule.onNodeWithText(
            "برای استفاده از این قابلیت‌ها نیازی به ساخت حساب کاربری",
            substring = true,
        ).assertExists()

        section.performClick()
        rule.onNodeWithText(
            "برای استفاده از این قابلیت‌ها نیازی به ساخت حساب کاربری",
            substring = true,
        ).assertDoesNotExist()
    }
}
