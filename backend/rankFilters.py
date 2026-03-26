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

SUNNDY_WEATHER_SUNNY_THRESHOLD = 7 # Hours per day
DRY_WEATHER_PRECIP_THRESHOLD = 1 # mm per day
WET_WEATHER_PRECIP_THRESHOLD = 5 # mm per day
LOW_HUMIDITY_THRESHOLD = 50 # percent
HIGH_HUMIDITY_THRESHOLD = 80 # percent

COSTAL_GEOGRAPHY_PROXIMITY_THRESHOLD = 50 # mi to coast
BEACH_GEOGRAPHY_PROXIMITY_THRESHOLD = 20 # mi to beach
URBAN_GEOGRAPHY_POPULATION_THRESHOLD = 1000000 # population
MOUNTAIN_GEOGRAPHY_ELEVATION_THRESHOLD = 1000 # m elevation
MOUNTAIN_GEOGRAPHY_ELEVATION_DS_THRESHOLD = 200 # m elevation difference from airport to surrounding area

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




def rank_temperature(airports: List[RankedAirport], filters: SearchFilters) -> List[RankedAirport]:
    conn = sqlite3.connect(DB_PATH)
    ranked = []

    for ranked_airport in airports:
        airport = ranked_airport.airport
        cursor = conn.cursor()
        cursor.execute("SELECT weather_temperature_yearly_average FROM airport_data WHERE iata_code = ?", (airport.iata_code,))
        result = cursor.fetchone()
        
        if result is None:
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
            else:
                score = 1.0

        ranked.append(RankedAirport(airport=airport, scores={"temperature": score}, percent_match=None))
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
    
    ranked_by_temp = rank_temperature(ranked_airports, parsed_filters)
    print(f"Ranked {len(ranked_by_temp)} airports by temperature:")
    for ranked in ranked_by_temp[:25]:  # Print the first 5 ranked airports
        print(ranked.airport.iata_code, ranked.airport.name, ranked.scores)
