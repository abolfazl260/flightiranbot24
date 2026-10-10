package com.abolfazl260.flightiranbot24.data.settings

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import com.abolfazl260.flightiranbot24.domain.settings.TravelerPreferences
import java.io.File
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class DataStoreTravelerPreferencesRepositoryTest {
    @get:Rule val temp = TemporaryFolder()

    @Test
    fun persistsLanguageAndDefaultPassportAcrossStoreRecreation() = runBlocking {
        val file = File(temp.root, "traveler.preferences_pb")
        val firstJob = SupervisorJob()
        val firstStore = PreferenceDataStoreFactory.create(
            scope = CoroutineScope(firstJob + Dispatchers.IO),
            produceFile = { file },
        )
        val first = DataStoreTravelerPreferencesRepository(firstStore)
        assertEquals(TravelerPreferences(), first.preferences.first())
        first.setLanguage("ar")
        first.setDefaultPassportCountry("TR")
        assertEquals(
            TravelerPreferences("ar", "TR"), first.preferences.first()
        )
        firstJob.cancelAndJoin()

        val secondJob = SupervisorJob()
        try {
            val newStore = PreferenceDataStoreFactory.create(
                scope = CoroutineScope(secondJob + Dispatchers.IO),
                produceFile = { file },
            )
            val recreated = DataStoreTravelerPreferencesRepository(newStore)
            assertEquals(
                TravelerPreferences("ar", "TR"), recreated.preferences.first()
            )
            recreated.setLanguage("en")
            assertEquals("en", recreated.preferences.first().language)
        } finally {
            secondJob.cancelAndJoin()
        }
    }

    @Test
    fun invalidInputsCannotCorruptSettings() = runBlocking {
        val job = SupervisorJob()
        val store = PreferenceDataStoreFactory.create(
            scope = CoroutineScope(job + Dispatchers.IO),
            produceFile = { File(temp.root, "validated.preferences_pb") },
        )
        try {
            val repository = DataStoreTravelerPreferencesRepository(store)
            assertThrows(IllegalArgumentException::class.java) {
                runBlocking { repository.setLanguage("de") }
            }
            assertThrows(IllegalArgumentException::class.java) {
                runBlocking { repository.setDefaultPassportCountry("UK/../../secret") }
            }
            assertEquals(TravelerPreferences(), repository.preferences.first())
            repository.setDefaultPassportCountry("IR")
            assertEquals("IR", repository.preferences.first().defaultPassportCountry)
        } finally {
            job.cancelAndJoin()
        }
    }
}
