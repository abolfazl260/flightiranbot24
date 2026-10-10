package com.abolfazl260.flightiranbot24.data.settings

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.abolfazl260.flightiranbot24.domain.settings.TravelerPreferences
import java.io.File
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class DataStoreTravelerPreferencesRepositoryTest {
    @get:Rule val temp = TemporaryFolder()

    @Test
    fun legacyLanguageDoesNotChangePersianPolicyOrErasePassport() = runBlocking {
        val file = File(temp.root, "traveler.preferences_pb")
        val firstJob = SupervisorJob()
        val firstStore = PreferenceDataStoreFactory.create(
            scope = CoroutineScope(firstJob + Dispatchers.IO),
            produceFile = { file },
        )
        firstStore.edit {
            it[stringPreferencesKey("language")] = "en"
            it[stringPreferencesKey("default_passport_country")] = "TR"
        }
        val first = DataStoreTravelerPreferencesRepository(firstStore)
        assertEquals(TravelerPreferences("TR"), first.preferences.first())
        first.setDefaultPassportCountry("IR")
        assertFalse(firstStore.data.first().contains(stringPreferencesKey("language")))
        firstJob.cancelAndJoin()

        val secondJob = SupervisorJob()
        try {
            val newStore = PreferenceDataStoreFactory.create(
                scope = CoroutineScope(secondJob + Dispatchers.IO),
                produceFile = { file },
            )
            val recreated = DataStoreTravelerPreferencesRepository(newStore)
            assertEquals(TravelerPreferences("IR"), recreated.preferences.first())
            recreated.setDefaultPassportCountry("AF")
            assertEquals("AF", recreated.preferences.first().defaultPassportCountry)
        } finally {
            secondJob.cancelAndJoin()
        }
    }

    @Test
    fun invalidCountriesCannotCorruptSettings() = runBlocking {
        val job = SupervisorJob()
        val store = PreferenceDataStoreFactory.create(
            scope = CoroutineScope(job + Dispatchers.IO),
            produceFile = { File(temp.root, "validated.preferences_pb") },
        )
        try {
            val repository = DataStoreTravelerPreferencesRepository(store)
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
