from __future__ import annotations

# ============================
# ======== IMPORTS ===========
# ============================

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from dataclasses import dataclass


# ================================
# ======== DATA MODELS ===========
# ================================

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


# ============================
# ======== HELPERS ===========
# ============================

def load_filters_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _first_present(data: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _normalize_string_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if not isinstance(value, list):
        return None

    normalized: List[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = " ".join(item.strip().lower().split())
            if cleaned:
                normalized.append(cleaned)
    return normalized


def _parse_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _parse_optional_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None


# =====================================
# ======== PARSING FUNCTIONS ==========
# =====================================

def parse_filters_json(data: Dict[str, Any]) -> SearchFilters:
    weather = _first_present(data, ("weather_preferences", "Weather", "weather"))
    conditions = _first_present(data, ("conditions_preferences", "Conditions", "conditions"))
    geography = _first_present(data, ("geography_preferences", "Geography", "geography"))
    max_connections = _first_present(data, ("max_connections", "maxConnections"))
    max_flight_time = _first_present(data, ("max_flight_time", "maxFlightTime"))
    budget_cap = _first_present(data, ("budget_cap", "budgetCap"))
    prefer_nonstop = _first_present(data, ("prefer_nonstop", "preferNonStop"))
    domestic_only = _first_present(data, ("domestic_only", "domesticOnly"))
    notes = _first_present(data, ("notes", "Notes"))

    return SearchFilters(
        weather_preferences=_normalize_string_list(weather),
        conditions_preferences=_normalize_string_list(conditions),
        geography_preferences=_normalize_string_list(geography),
        max_connections=_parse_optional_int(max_connections),
        max_flight_time=_parse_optional_int(max_flight_time),
        budget_cap=_parse_optional_int(budget_cap),
        prefer_nonstop=_parse_optional_bool(prefer_nonstop),
        domestic_only=_parse_optional_bool(domestic_only),
        notes=notes if isinstance(notes, str) else None
    )


# =======================================
# =========== LOCAL TESTING =============
# =======================================

if __name__ == "__main__":
    filters_path = Path("data/filters-sample.json")
    filters_data = load_filters_json(filters_path)
    print(filters_data)
    parsed_filters = parse_filters_json(filters_data)
    print(parsed_filters)
