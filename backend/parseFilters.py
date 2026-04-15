from __future__ import annotations

# ============================
# ======== IMPORTS ===========
# ============================

import json
from typing import Any, Dict, Iterable, List, Optional

from models import SearchFilters


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
    return normalized if normalized else None


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


def _parse_optional_str(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def _normalize_airport_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if not isinstance(value, list):
        return None

    normalized: List[str] = []
    seen = set()
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip().upper()
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized if normalized else None


# =====================================
# ======== PARSING FUNCTIONS ==========
# =====================================

def parse_filters_json(data: Dict[str, Any]) -> SearchFilters:
    departure_date = _first_present(data, ("departure_date", "departureDate"))
    return_date = _first_present(data, ("return_date", "returnDate", "arrival_date", "arrivalDate"))
    airports = _first_present(data, ("airports", "airport_preferences", "airport"))
    weather = _first_present(data, ("weather_preferences", "Weather", "weather"))
    conditions = _first_present(data, ("conditions_preferences", "Conditions", "conditions"))
    geography = _first_present(data, ("geography_preferences", "Geography", "geography"))
    max_connections = _first_present(data, ("max_connections", "maxConnections"))
    max_flight_time = _first_present(data, ("max_flight_time", "maxFlightTime"))
    max_flight_cost = _first_present(data, ("max_flight_cost", "maxFlightCost"))
    budget_cap = _first_present(data, ("budget_cap", "budgetCap"))
    prefer_nonstop = _first_present(data, ("prefer_nonstop", "preferNonStop"))
    domestic_only = _first_present(data, ("domestic_only", "domesticOnly"))
    notes = _first_present(data, ("notes", "Notes"))

    return SearchFilters(
        departure_date=_parse_optional_str(departure_date),
        return_date=_parse_optional_str(return_date),
        airports=_normalize_airport_list(airports),
        weather_preferences=_normalize_string_list(weather),
        conditions_preferences=_normalize_string_list(conditions),
        geography_preferences=_normalize_string_list(geography),
        max_connections=_parse_optional_int(max_connections),
        max_flight_time=_parse_optional_int(max_flight_time),
        max_flight_cost=_parse_optional_int(max_flight_cost),
        budget_cap=_parse_optional_int(budget_cap),
        prefer_nonstop=_parse_optional_bool(prefer_nonstop),
        domestic_only=_parse_optional_bool(domestic_only),
        notes=notes if isinstance(notes, str) else None
    )


def parse_filters_api_json(payload: Any) -> SearchFilters:
    if payload is None:
        return SearchFilters()

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return SearchFilters()

    if not isinstance(payload, dict):
        return SearchFilters()

    return parse_filters_json(payload)
