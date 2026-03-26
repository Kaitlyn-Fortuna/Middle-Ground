from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchFilters:

    weather_preferences: Optional[List[str]] = None  # user-selected weather preferences
    conditions_preferences: Optional[List[str]] = None  # user-selected conditions preferences
    geography_preferences: Optional[List[str]] = None  # user-selected geography preferences

    max_connections: Optional[int] = None  # user-selected maximum number of connections
    max_flight_time: Optional[int] = None  # user-selected maximum flight time in hours
    budget_cap: Optional[int] = None  # user-selected budget cap in USD
    prefer_nonstop: Optional[bool] = None  # user-selected preference for nonstop flights
    domestic_only: Optional[bool] = None  # user-selected preference for domestic flights only

    notes: Optional[str] = None  # user-entered notes or comments


def load_filters_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    

def parse_filters_json(data: Dict[str, Any]) -> SearchFilters:
    return SearchFilters(
        weather_preferences=data.get("weather_preferences"),
        conditions_preferences=data.get("conditions_preferences"),
        geography_preferences=data.get("geography_preferences"),
        max_connections=data.get("max_connections"),
        max_flight_time=data.get("max_flight_time"),
        budget_cap=data.get("budget_cap"),
        prefer_nonstop=data.get("prefer_nonstop"),
        domestic_only=data.get("domestic_only"),
        notes=data.get("notes")
    )



if __name__ == "__main__":
    filters_path = Path("/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring 2026/EECS3550/MiddleGround/backend/filters-sample.json")
    filters_data = load_filters_json(filters_path)
    print(filters_data)
    parsed_filters = parse_filters_json(filters_data)
    print(parsed_filters)