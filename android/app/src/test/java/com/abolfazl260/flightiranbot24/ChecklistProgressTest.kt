package com.abolfazl260.flightiranbot24

import android.content.Context
import android.widget.CheckBox
import android.widget.ProgressBar
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/** Verifies live, user-driven progress without deleting legacy checkbox choices. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class ChecklistProgressTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()

    @Before
    fun clean() {
        context.getSharedPreferences(ChecklistActivity.PREFS, Context.MODE_PRIVATE)
            .edit().clear().commit()
    }

    @After
    fun cleanup() = clean()

    @Test
    fun percentageAlwaysTracksActualSelectedCount() {
        assertEquals(0, ChecklistActivity.completionPercent(0, 12))
        assertEquals(8, ChecklistActivity.completionPercent(1, 12))
        assertEquals(50, ChecklistActivity.completionPercent(6, 12))
        assertEquals(100, ChecklistActivity.completionPercent(12, 12))
        assertThrows(IllegalArgumentException::class.java) {
            ChecklistActivity.completionPercent(2, 0)
        }
        assertThrows(IllegalArgumentException::class.java) {
            ChecklistActivity.completionPercent(13, 12)
        }
    }

    @Test
    fun expandedTasksArePersistedAndProgressRespondsToChanges() {
        val activity = Robolectric.buildActivity(ChecklistActivity::class.java).setup().get()
        val first = activity.findViewById<CheckBox>(R.id.checkPassport)
        val boarding = activity.findViewById<CheckBox>(R.id.checkBoarding)
        val percent = activity.findViewById<TextView>(R.id.checklistPercent)
        val progress = activity.findViewById<ProgressBar>(R.id.checklistProgressBar)

        assertFalse(first.isChecked)
        assertEquals(100, progress.max)
        assertEquals(activity.getString(R.string.checklist_progress_percent, 0), percent.text)
        first.isChecked = true
        boarding.isChecked = true
        assertEquals(activity.getString(R.string.checklist_progress_percent, 17), percent.text)
        assertTrue(context.getSharedPreferences(ChecklistActivity.PREFS, Context.MODE_PRIVATE)
            .getBoolean("boarding", false))
        activity.finish()
    }

    @Test
    fun existingSixTaskKeysSurviveNewVersion() {
        val prefs = context.getSharedPreferences(ChecklistActivity.PREFS, Context.MODE_PRIVATE)
        prefs.edit().putBoolean("passport", true).putBoolean("visa", true)
            .putBoolean("tickets", true).putBoolean("insurance", true)
            .putBoolean("money", true).putBoolean("essentials", true).commit()
        val activity = Robolectric.buildActivity(ChecklistActivity::class.java).setup().get()
        assertEquals(
            activity.getString(R.string.checklist_progress_percent, 50),
            activity.findViewById<TextView>(R.id.checklistPercent).text,
        )
        assertTrue(activity.findViewById<CheckBox>(R.id.checkTickets).isChecked)
        assertFalse(activity.findViewById<CheckBox>(R.id.checkEmergency).isChecked)
        assertEquals(12, ChecklistActivity.KEYS.size)
        assertEquals(12, ChecklistActivity.VIEW_IDS.size)
        activity.finish()
    }

    @Test
    fun checklistRowsStayCompactWithoutShrinkingIcons() {
        val activity = Robolectric.buildActivity(ChecklistActivity::class.java).setup().get()
        val density = activity.resources.displayMetrics.density
        for (id in ChecklistActivity.VIEW_IDS) {
            val item = activity.findViewById<CheckBox>(id)
            assertTrue(item.minimumHeight >= (68 * density).toInt())
            assertTrue(item.minimumHeight <= (72 * density).toInt())
            assertTrue((item.layoutParams as android.widget.LinearLayout.LayoutParams).topMargin >= (8 * density).toInt())
            assertTrue((item.layoutParams as android.widget.LinearLayout.LayoutParams).topMargin <= (10 * density).toInt())
            assertTrue(item.compoundDrawablesRelative[2] != null)
            assertTrue(item.compoundDrawablesRelative[2].bounds.width() >= (52 * density).toInt() - 1)
        }
        activity.finish()
    }

    @Test
    fun progressShowsTwentyFivePercentAfterThreeSelections() {
        val activity = Robolectric.buildActivity(ChecklistActivity::class.java).setup().get()
        for (id in ChecklistActivity.VIEW_IDS.take(3)) {
            activity.findViewById<CheckBox>(id).isChecked = true
        }
        assertEquals(
            activity.getString(R.string.checklist_progress_percent, 25),
            activity.findViewById<TextView>(R.id.checklistPercent).text
        )
        activity.finish()
    }
}
