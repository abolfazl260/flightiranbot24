package com.abolfazl260.flightiranbot24.data.airports;

import android.content.Context;
import androidx.room.Database;
import androidx.room.Room;
import androidx.room.RoomDatabase;

/**
 * Public data cache, independent of the legacy native checklist preferences.
 * Schema v1 has no prior migration. Future version bumps MUST add an explicit
 * Room Migration and a fixture-based preservation test, never destructive fallback.
 */
@Database(entities = {CachedAirportEntity.class}, version = 1, exportSchema = true)
public abstract class TravelCacheDatabase extends RoomDatabase {
    private static volatile TravelCacheDatabase instance;

    public abstract AirportCacheDao airportCacheDao();

    public static TravelCacheDatabase getInstance(Context context) {
        TravelCacheDatabase result = instance;
        if (result == null) {
            synchronized (TravelCacheDatabase.class) {
                result = instance;
                if (result == null) {
                    result = Room.databaseBuilder(
                            context.getApplicationContext(),
                            TravelCacheDatabase.class,
                            "travel_public_cache.db"
                    ).build();
                    instance = result;
                }
            }
        }
        return result;
    }
}
