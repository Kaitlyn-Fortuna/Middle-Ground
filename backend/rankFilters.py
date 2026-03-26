from __future__ import annotations

from dataclasses import dataclass, field
import math
import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Callable

from parseFilters import SearchFilters

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


HOT_WEATHER_TEMP_THRESHOLD = 85.0  # Fahrenheit
WARM_WETHER_TEMP_THRESHOLD = 70.0  # Fahrenheit
MILD_WEATHER_TEMP_THRESHOLD = 55.0  # Fahrenheit
COOL_WEATHER_TEMP_THRESHOLD = 40.0  # Fahrenheit
COLD_WEATHER_TEMP_THRESHOLD = 00.0  # Fahrenheit

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



def import_airport_data(db_path: Path) -> List[Airport]:
    conn = sqlite3.connect(db_path)
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












if __name__ == "__main__":
    db_path = Path("data/airport_data.db")
    airports = import_airport_data(db_path)
    print(f"Imported {len(airports)} airports:")
    for airport in airports[:5]:  # Print the first 5 airports
        print(airport)
    ranked_airports = initialize_ranked_airports(airports)
    print(f"Initialized {len(ranked_airports)} ranked airports:")
    for ranked in ranked_airports[:5]:  # Print the first 5 ranked airports
        print(ranked)