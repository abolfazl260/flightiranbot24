package com.abolfazl260.flightiranbot24

import android.content.Context
import android.graphics.Color
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import kotlin.math.pow

/** WCAG 2.2 AA text contrast check for resource-backed Android / Compose colors. */
@RunWith(RobolectricTestRunner::class)
class AdvertioContrastTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()

    private fun luminance(color: Int): Double {
        fun channel(value: Int): Double {
            val c = value / 255.0
            return if (c <= 0.04045) c / 12.92 else ((c + 0.055) / 1.055).pow(2.4)
        }
        return 0.2126 * channel(Color.red(color)) +
            0.7152 * channel(Color.green(color)) +
            0.0722 * channel(Color.blue(color))
    }

    private fun contrast(foreground: Int, background: Int): Double {
        val lighter = maxOf(luminance(foreground), luminance(background))
        val darker = minOf(luminance(foreground), luminance(background))
        return (lighter + 0.05) / (darker + 0.05)
    }

    private fun assertReadable(foreground: Int, background: Int) {
        val foregroundColor = context.getColor(foreground)
        val backgroundColor = context.getColor(background)
        val value = contrast(foregroundColor, backgroundColor)
        assertTrue("Contrast $value must reach WCAG AA 4.5:1", value >= 4.5)
    }

    @Test fun bodyAndBrandTextPassNormalTextContrast() {
        assertReadable(R.color.navy, R.color.white)
        assertReadable(R.color.navy, R.color.pale)
        assertReadable(R.color.slate, R.color.white)
        assertReadable(R.color.slate, R.color.surface_variant)
        assertReadable(R.color.teal, R.color.white)
        assertReadable(R.color.teal, R.color.pale)
        assertReadable(R.color.white, R.color.navy)
        assertReadable(R.color.white, R.color.teal)
        assertReadable(R.color.error, R.color.white)
    }
}
