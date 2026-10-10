package com.abolfazl260.flightiranbot24.data.airports;

import androidx.annotation.NonNull;
import androidx.room.Entity;
import androidx.room.PrimaryKey;

/**
 * Room v1 is a separate cache; the original assets and Java offline airport
 * directory remain untouched until the dedicated AIR tasks.
 */
@Entity(tableName = "airport_cache")
public class CachedAirportEntity {
    @PrimaryKey @NonNull public String iata;
    @NonNull public String country;
    @NonNull public String name;
    @NonNull public String timezone;
    @NonNull public String dataVersion;

    public CachedAirportEntity(
            @NonNull String iata,
            @NonNull String country,
            @NonNull String name,
            @NonNull String timezone,
            @NonNull String dataVersion) {
        this.iata = iata;
        this.country = country;
        this.name = name;
        this.timezone = timezone;
        this.dataVersion = dataVersion;
    }
}
