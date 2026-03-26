from __future__ import annotations

from dataclasses import dataclass, field
import math
import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Callable

from parseFilters import SearchFilters, load_filters_json, parse_filters_json

@dataclass(frozen=True)
class Airport:
    iata_code: str
    name: str
    iso_country: str
    iso_region: str
    airport_type: str
    latitude: float
    longitude: float

@dataclass(frozen=True)
class RankedAirport:
    airport: Airport
    scores: Optional[Dict[str, float]]
    percent_match: Optional[float]


@dataclass(frozen=True)
class RankResult:
    ranked: List[RankedAirport]
    active_score_keys: List[str]
    diagnostics: Dict[str, object] = field(default_factory=dict)

DB_PATH = Path("data/airport_data.db")

HOT_WEATHER_TEMP_THRESHOLD = [40.0, 30.0]  # Celsius
WARM_WETHER_TEMP_THRESHOLD = [30.0, 22.0]  # Celsius
MILD_WEATHER_TEMP_THRESHOLD = [22.0, 14.0]  # Celsius
COOL_WEATHER_TEMP_THRESHOLD = [14.0, 4.0]  # Celsius
COLD_WEATHER_TEMP_THRESHOLD = [4.0, -20.0]  # Celsius

SUNNDY_WEATHER_SUNNY_THRESHOLD = 9.5 # Hours per day
DRY_WEATHER_PRECIP_THRESHOLD = 1 # mm per day
WET_WEATHER_PRECIP_THRESHOLD = 4 # mm per day
LOW_HUMIDITY_THRESHOLD = 50 # percent
HIGH_HUMIDITY_THRESHOLD = 75 # percent

COSTAL_GEOGRAPHY_PROXIMITY_THRESHOLD = 50 # mi to coast
BEACH_GEOGRAPHY_PROXIMITY_THRESHOLD = 20 # mi to beach
URBAN_GEOGRAPHY_POPULATION_THRESHOLD = 1000000 # population
MOUNTAIN_GEOGRAPHY_ELEVATION_THRESHOLD = 1000 # m elevation
MOUNTAIN_GEOGRAPHY_ELEVATION_SD_THRESHOLD = 200 # m elevation standard deviation from airport to surrounding area

TEMPERATURE_BANDS: Dict[str, Tuple[float, float]] = {
    "hot": (HOT_WEATHER_TEMP_THRESHOLD[1], HOT_WEATHER_TEMP_THRESHOLD[0]),
    "warm": (WARM_WETHER_TEMP_THRESHOLD[1], WARM_WETHER_TEMP_THRESHOLD[0]),
    "mild": (MILD_WEATHER_TEMP_THRESHOLD[1], MILD_WEATHER_TEMP_THRESHOLD[0]),
    "cool": (COOL_WEATHER_TEMP_THRESHOLD[1], COOL_WEATHER_TEMP_THRESHOLD[0]),
    "cold": (COLD_WEATHER_TEMP_THRESHOLD[1], COLD_WEATHER_TEMP_THRESHOLD[0]),
}


def import_airport_data() -> List[Airport]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT iata_code, name, iso_country, iso_region, type, latitude, longitude FROM airport_data")
    rows = cursor.fetchall()

    airports = []
    for row in rows:
        airport = Airport(
            iata_code=row[0],
            name=row[1],
            iso_country=row[2],
            iso_region=row[3],
            airport_type=row[4],
            latitude=row[5],
            longitude=row[6]
        )
        airports.append(airport)

    conn.close()
    return airports


def initialize_ranked_airports(airports: List[Airport]) -> List[RankedAirport]:
    return [RankedAirport(airport=airport, scores=None, percent_match=None) for airport in airports]


def _append_score(ranked_airport: RankedAirport, score_key: str, score_value: float) -> RankedAirport:
    merged_scores = dict(ranked_airport.scores or {})
    merged_scores[score_key] = score_value
    return RankedAirport(
        airport=ranked_airport.airport,
        scores=merged_scores,
        percent_match=ranked_airport.percent_match,
    )




def rank_weather_temperature(airports: List[RankedAirport], filters: SearchFilters) -> List[RankedAirport]:
    conn = sqlite3.connect(DB_PATH)
    ranked = []

    if filters.weather_preferences is None:
        return airports

    for ranked_airport in airports:
        airport = ranked_airport.airport
        cursor = conn.cursor()
        cursor.execute("SELECT weather_temperature_yearly_average FROM airport_data WHERE iata_code = ?", (airport.iata_code,))
        result = cursor.fetchone()
        
        if result is None:
            ranked.append(ranked_airport)
            continue

        score = 0.0

        if filters.weather_preferences is not None:
            temp_band: List[Optional[float]] = [None, None]
            score = 0.0

            if "hot" in filters.weather_preferences:
                if temp_band[0] is None or HOT_WEATHER_TEMP_THRESHOLD[0] > temp_band[0]:
                    temp_band[0] = HOT_WEATHER_TEMP_THRESHOLD[0]
                if temp_band[1] is None or HOT_WEATHER_TEMP_THRESHOLD[1] < temp_band[1]:
                    temp_band[1] = HOT_WEATHER_TEMP_THRESHOLD[1]

            if "warm" in filters.weather_preferences:
                if temp_band[0] is None or WARM_WETHER_TEMP_THRESHOLD[0] > temp_band[0]:
                    temp_band[0] = WARM_WETHER_TEMP_THRESHOLD[0]
                if temp_band[1] is None or WARM_WETHER_TEMP_THRESHOLD[1] < temp_band[1]:
                    temp_band[1] = WARM_WETHER_TEMP_THRESHOLD[1]

            if "mild" in filters.weather_preferences:
                if temp_band[0] is None or MILD_WEATHER_TEMP_THRESHOLD[0] > temp_band[0]:
                    temp_band[0] = MILD_WEATHER_TEMP_THRESHOLD[0]
                if temp_band[1] is None or MILD_WEATHER_TEMP_THRESHOLD[1] < temp_band[1]:
                    temp_band[1] = MILD_WEATHER_TEMP_THRESHOLD[1]

            if "cool" in filters.weather_preferences:
                if temp_band[0] is None or COOL_WEATHER_TEMP_THRESHOLD[0] > temp_band[0]:
                    temp_band[0] = COOL_WEATHER_TEMP_THRESHOLD[0]
                if temp_band[1] is None or COOL_WEATHER_TEMP_THRESHOLD[1] < temp_band[1]:
                    temp_band[1] = COOL_WEATHER_TEMP_THRESHOLD[1]

            if "cold" in filters.weather_preferences:
                if temp_band[0] is None or COLD_WEATHER_TEMP_THRESHOLD[0] > temp_band[0]:
                    temp_band[0] = COLD_WEATHER_TEMP_THRESHOLD[0]
                if temp_band[1] is None or COLD_WEATHER_TEMP_THRESHOLD[1] < temp_band[1]:
                    temp_band[1] = COLD_WEATHER_TEMP_THRESHOLD[1]

            if temp_band[0] is not None and temp_band[1] is not None:
                if temp_band[0] >= result[0] >= temp_band[1]:
                    score = 1.0
                else:
                    score = max(
                        0.0,
                        1.0 - (max(abs(result[0] - temp_band[0]), abs(result[0] - temp_band[1])) / 100.0),
                    )

        ranked.append(_append_score(ranked_airport, "temperature", score))

    conn.close()
    return ranked


def rank_condition_sun(airports: List[RankedAirport], filters: SearchFilters) -> List[RankedAirport]:
    conn = sqlite3.connect(DB_PATH)
    ranked = []

    if filters.conditions_preferences is None or "sunny" not in filters.conditions_preferences:
        return airports

    for ranked_airport in airports:
        airport = ranked_airport.airport
        cursor = conn.cursor()
        cursor.execute("SELECT weather_sun_yearly_average FROM airport_data WHERE iata_code = ?", (airport.iata_code,))
        result = cursor.fetchone()
        
        if result is None:
            ranked.append(ranked_airport)
            continue

        score = 0.0

        if filters.conditions_preferences is not None:
            if "sunny" in filters.conditions_preferences:
                if result[0] >= SUNNDY_WEATHER_SUNNY_THRESHOLD:
                    score = 1.0
                else:
                    score = max(0.0, result[0] / SUNNDY_WEATHER_SUNNY_THRESHOLD)

        ranked.append(_append_score(ranked_airport, "sunny", score))

    conn.close()
    return ranked


def rank_condition_rain(airports: List[RankedAirport], filters: SearchFilters) -> List[RankedAirport]:
    conn = sqlite3.connect(DB_PATH)
    ranked = []

    if filters.conditions_preferences is None or ("wet" not in filters.conditions_preferences and "dry" not in filters.conditions_preferences):
        return airports

    for ranked_airport in airports:
        airport = ranked_airport.airport
        cursor = conn.cursor()
        cursor.execute("SELECT weather_precip_yearly_average FROM airport_data WHERE iata_code = ?", (airport.iata_code,))
        result = cursor.fetchone()
        
        if result is None:
            ranked.append(ranked_airport)
            continue

        score = 0.0

        if filters.conditions_preferences is not None:
            if "dry" in filters.conditions_preferences and "wet" in filters.conditions_preferences:
                score_key = "dry/wet"
                if result[0] <= DRY_WEATHER_PRECIP_THRESHOLD:
                    score = 1.0
                elif result[0] >= WET_WEATHER_PRECIP_THRESHOLD:
                    score = 1.0
                else:
                    dry_score = max(0.0, 1.0 - (result[0] / (DRY_WEATHER_PRECIP_THRESHOLD * 10)))
                    wet_score = max(0.0, result[0] / WET_WEATHER_PRECIP_THRESHOLD)
                    score = max(dry_score, wet_score)
            elif "dry" in filters.conditions_preferences:
                score_key = "dry"
                if result[0] <= DRY_WEATHER_PRECIP_THRESHOLD:
                    score = 1.0
                elif result[0] >= WET_WEATHER_PRECIP_THRESHOLD:
                    score = 0.0
                else:
                    score = (WET_WEATHER_PRECIP_THRESHOLD - result[0]) / (WET_WEATHER_PRECIP_THRESHOLD - DRY_WEATHER_PRECIP_THRESHOLD)
            elif "wet" in filters.conditions_preferences:
                score_key = "wet"
                if result[0] >= WET_WEATHER_PRECIP_THRESHOLD:
                    score = 1.0
                else:
                    score = max(0.0, result[0] / WET_WEATHER_PRECIP_THRESHOLD)

        ranked.append(_append_score(ranked_airport, score_key, score))

    conn.close()
    return ranked


def rank_condition_humidity(airports: List[RankedAirport], filters: SearchFilters) -> List[RankedAirport]:
    conn = sqlite3.connect(DB_PATH)
    ranked = []

    if filters.conditions_preferences is None or ("low humidity" not in filters.conditions_preferences and "high humidity" not in filters.conditions_preferences):
        return airports

    for ranked_airport in airports:
        airport = ranked_airport.airport
        cursor = conn.cursor()
        cursor.execute("SELECT weather_humidity_yearly_average FROM airport_data WHERE iata_code = ?", (airport.iata_code,))
        result = cursor.fetchone()
        
        if result is None:
            ranked.append(ranked_airport)
            continue

        score = 0.0

        if filters.conditions_preferences is not None:
            if "low humidity" in filters.conditions_preferences and "high humidity" in filters.conditions_preferences:
                score_key = "low/high humidity"
                if result[0] <= LOW_HUMIDITY_THRESHOLD:
                    score = 1.0
                elif result[0] >= HIGH_HUMIDITY_THRESHOLD:
                    score = 1.0
                else:
                    low_score = max(0.0, 1.0 - (result[0] / (LOW_HUMIDITY_THRESHOLD * 10)))
                    high_score = max(0.0, result[0] / HIGH_HUMIDITY_THRESHOLD)
                    score = max(low_score, high_score)
            elif "low humidity" in filters.conditions_preferences:
                score_key = "low humidity"
                if result[0] <= LOW_HUMIDITY_THRESHOLD:
                    score = 1.0
                elif result[0] >= HIGH_HUMIDITY_THRESHOLD:
                    score = 0.0
                else:
                    score = (HIGH_HUMIDITY_THRESHOLD - result[0]) / (HIGH_HUMIDITY_THRESHOLD - LOW_HUMIDITY_THRESHOLD)
            elif "high humidity" in filters.conditions_preferences:
                score_key = "high humidity"
                if result[0] >= HIGH_HUMIDITY_THRESHOLD:
                    score = 1.0
                else:
                    score = max(0.0, result[0] / HIGH_HUMIDITY_THRESHOLD)

        ranked.append(_append_score(ranked_airport, score_key, score))

    conn.close()
    return ranked


def rank_geography_coastal(airports: List[RankedAirport], filters: SearchFilters) -> List[RankedAirport]:
    conn = sqlite3.connect(DB_PATH)
    ranked = []

    if filters.geography_preferences is None or ("coastal" not in filters.geography_preferences):
        return airports

    for ranked_airport in airports:
        airport = ranked_airport.airport
        cursor = conn.cursor()
        cursor.execute("SELECT coastal_distance FROM airport_data WHERE iata_code = ?", (airport.iata_code,))
        result = cursor.fetchone()
        
        if result is None:
            ranked.append(ranked_airport)
            continue

        score = 0.0

        if filters.geography_preferences is not None and ("coastal" in filters.geography_preferences):
            score_key = "coastal"
            if result[0] <= COSTAL_GEOGRAPHY_PROXIMITY_THRESHOLD:
                score = 1.0
            else:
                score = max(0.0, 1.0 - ((result[0] - COSTAL_GEOGRAPHY_PROXIMITY_THRESHOLD) / 100.0))

        ranked.append(_append_score(ranked_airport, score_key, score))

    conn.close()
    return ranked


def rank_geography_beach(airports: List[RankedAirport], filters: SearchFilters) -> List[RankedAirport]:
    conn = sqlite3.connect(DB_PATH)
    ranked = []

    if filters.geography_preferences is None or ("beach" not in filters.geography_preferences):
        return airports

    for ranked_airport in airports:
        airport = ranked_airport.airport
        cursor = conn.cursor()
        cursor.execute("SELECT beach_distance FROM airport_data WHERE iata_code = ?", (airport.iata_code,))
        result = cursor.fetchone()
        
        if result is None:
            ranked.append(ranked_airport)
            continue

        score = 0.0

        if filters.geography_preferences is not None and ("beach" in filters.geography_preferences):
            score_key = "beach"
            if result[0] <= BEACH_GEOGRAPHY_PROXIMITY_THRESHOLD:
                score = 1.0
            else:
                score = max(0.0, 1.0 - ((result[0] - BEACH_GEOGRAPHY_PROXIMITY_THRESHOLD) / 100.0))

        ranked.append(_append_score(ranked_airport, score_key, score))

    conn.close()
    return ranked


def rank_geography_urban(airports: List[RankedAirport], filters: SearchFilters) -> List[RankedAirport]:
    conn = sqlite3.connect(DB_PATH)
    ranked = []

    if filters.geography_preferences is None or ("urban" not in filters.geography_preferences):
        return airports

    for ranked_airport in airports:
        airport = ranked_airport.airport
        cursor = conn.cursor()
        cursor.execute("SELECT population FROM airport_data WHERE iata_code = ?", (airport.iata_code,))
        result = cursor.fetchone()
        
        if result is None:
            ranked.append(ranked_airport)
            continue

        score = 0.0

        if filters.geography_preferences is not None and ("urban" in filters.geography_preferences):
            score_key = "urban"
            if result[0] >= URBAN_GEOGRAPHY_POPULATION_THRESHOLD:
                score = 1.0
            else:
                score = max(0.0, result[0] / URBAN_GEOGRAPHY_POPULATION_THRESHOLD)
                
        ranked.append(_append_score(ranked_airport, score_key, score))

    conn.close()
    return ranked


def rank_geography_mountainous(airports: List[RankedAirport], filters: SearchFilters) -> List[RankedAirport]:
    conn = sqlite3.connect(DB_PATH)
    ranked = []

    if filters.geography_preferences is None or ("mountainous" not in filters.geography_preferences):
        return airports

    for ranked_airport in airports:
        airport = ranked_airport.airport
        cursor = conn.cursor()
        cursor.execute("SELECT relief_value, stddev_value FROM airport_data WHERE iata_code = ?", (airport.iata_code,))
        result = cursor.fetchone()
        
        if result is None:
            ranked.append(ranked_airport)
            continue

        elevation_score = 0.0
        rugged_score = 0.0

        if filters.geography_preferences is not None and ("mountainous" in filters.geography_preferences):
            score_key = "mountainous"
            if result[0] >= MOUNTAIN_GEOGRAPHY_ELEVATION_THRESHOLD:
                elevation_score = 1.0
            else:
                elevation_score = max(0.0, result[0] / MOUNTAIN_GEOGRAPHY_ELEVATION_THRESHOLD)

            if result[1] >= MOUNTAIN_GEOGRAPHY_ELEVATION_SD_THRESHOLD:
                rugged_score = 1.0
            else:
                rugged_score = max(0.0, result[1] / MOUNTAIN_GEOGRAPHY_ELEVATION_SD_THRESHOLD)

        score = ((elevation_score * 0.65) + (rugged_score * 0.35))

        ranked.append(_append_score(ranked_airport, score_key, score))

    conn.close()
    return ranked








if __name__ == "__main__":
    filters_path = Path("/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring 2026/EECS3550/MiddleGround/data/filters-test.json")
    filters_data = load_filters_json(filters_path)
    parsed_filters = parse_filters_json(filters_data)
    
    airports = import_airport_data()
    print(f"Imported {len(airports)} airports:")
    for airport in airports[:5]:  # Print the first 5 airports
        print(airport)
    ranked_airports = initialize_ranked_airports(airports)
    print(f"Initialized {len(ranked_airports)} ranked airports:")
    for ranked in ranked_airports[:5]:  # Print the first 5 ranked airports
        print(ranked)
    
    ranked_airports = rank_weather_temperature(ranked_airports, parsed_filters)
    print(f"Ranked {len(ranked_airports)} airports by temperature:")
    for ranked in ranked_airports[:25]:  # Print the first 25 ranked airports
        print(ranked.airport.iata_code, ranked.airport.name, ranked.scores)

    ranked_airports = rank_condition_sun(ranked_airports, parsed_filters)
    print(f"Ranked {len(ranked_airports)} airports by sun:")
    for ranked in ranked_airports[:25]:  # Print the first 25 ranked airports
        print(ranked.airport.iata_code, ranked.airport.name, ranked.scores)

    ranked_airports = rank_condition_rain(ranked_airports, parsed_filters)
    print(f"Ranked {len(ranked_airports)} airports by rain:")
    for ranked in ranked_airports[:25]:  # Print the first 25 ranked airports
        print(ranked.airport.iata_code, ranked.airport.name, ranked.scores) 

    ranked_airports = rank_condition_humidity(ranked_airports, parsed_filters)
    print(f"Ranked {len(ranked_airports)} airports by humidity:")
    for ranked in ranked_airports[:25]:  # Print the first 25 ranked airports
        print(ranked.airport.iata_code, ranked.airport.name, ranked.scores)
    
    ranked_airports = rank_geography_coastal(ranked_airports, parsed_filters)
    print(f"Ranked {len(ranked_airports)} airports by coastal geography:")
    for ranked in ranked_airports[:25]:  # Print the first 25 ranked airports
        print(ranked.airport.iata_code, ranked.airport.name, ranked.scores)

    ranked_airports = rank_geography_beach(ranked_airports, parsed_filters)
    print(f"Ranked {len(ranked_airports)} airports by beach geography:")
    for ranked in ranked_airports[:25]:  # Print the first 25 ranked airports
        print(ranked.airport.iata_code, ranked.airport.name, ranked.scores)

    ranked_airports = rank_geography_urban(ranked_airports, parsed_filters)
    print(f"Ranked {len(ranked_airports)} airports by urban geography:")
    for ranked in ranked_airports[:25]:  # Print the first 25 ranked airports
        print(ranked.airport.iata_code, ranked.airport.name, ranked.scores) 

    ranked_airports = rank_geography_mountainous(ranked_airports, parsed_filters)
    print(f"Ranked {len(ranked_airports)} airports by mountainous geography:")
    for ranked in ranked_airports[:25]:  # Print the first 25 ranked airports
        print(ranked.airport.iata_code, ranked.airport.name, ranked.scores)
