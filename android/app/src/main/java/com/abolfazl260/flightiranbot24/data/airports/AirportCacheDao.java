package com.abolfazl260.flightiranbot24.data.airports;

import androidx.annotation.Nullable;
import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;
import java.util.List;

@Dao
public interface AirportCacheDao {
    @Query("SELECT * FROM airport_cache ORDER BY iata")
    List<CachedAirportEntity> all();

    @Nullable
    @Query("SELECT * FROM airport_cache WHERE iata = :iata LIMIT 1")
    CachedAirportEntity findByIata(String iata);

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    void upsertAll(List<CachedAirportEntity> airports);

    @Query("DELETE FROM airport_cache")
    void clear();
}
