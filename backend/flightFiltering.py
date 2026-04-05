from __future__ import annotations

# ============================
# ======== IMPORTS ===========
# ============================

import logging
import math
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from datetime import date, datetime

from flightApiProvider import (
    FlightApiClient,
    FlightApiError,
    FlightApiInputError,
)
from airportFiltering import (
    TEMPERATURE_BANDS,
    SUNNDY_WEATHER_SUNNY_THRESHOLD,
    DRY_WEATHER_PRECIP_THRESHOLD,
    WET_WEATHER_PRECIP_THRESHOLD,
    LOW_HUMIDITY_THRESHOLD,
    HIGH_HUMIDITY_THRESHOLD,
    COSTAL_GEOGRAPHY_PROXIMITY_THRESHOLD,
    BEACH_GEOGRAPHY_PROXIMITY_THRESHOLD,
    URBAN_GEOGRAPHY_POPULATION_SOFT_CAP,
    MOUNTAIN_GEOGRAPHY_ELEVATION_THRESHOLD,
    MOUNTAIN_GEOGRAPHY_ELEVATION_SD_THRESHOLD,
    DB_PATH,
    RankedAirport,
    import_airport_data,
    initialize_ranked_airports,
    overall_rank,
    run_all_ranks,
)
from models import (
    Flight,
    SearchFilters,
    FlightRankResult, 
    RankedFlight
)


# ====================================
# ======== SCORING CONSTANTS =========
# ====================================

MAX_DESTINATION_CANDIDATES = 10
MIN_COMBINED_RESULTS_TARGET = 5
logger = logging.getLogger("middleground.flightfilter")



# ============================
# ======== HELPERS ===========
# ============================

def _append_flight_score(ranked_flight: RankedFlight, score_key: str, score_value: float) -> RankedFlight:
    merged_scores = dict(ranked_flight.scores or {})
    merged_scores[score_key] = score_value
    return RankedFlight(
        flight=ranked_flight.flight,
        destination_airport_rank=ranked_flight.destination_airport_rank,
        scores=merged_scores,
        percent_match=ranked_flight.percent_match,
    )


def initialize_ranked_flights(flights: List[Flight], destination_rank_map: Optional[Dict[str, RankedAirport]] = None) -> List[RankedFlight]:
    rank_map = destination_rank_map or {}
    ranked: List[RankedFlight] = []

    for flight in flights:
        destination_rank = rank_map.get((flight.arrival_iata or "").upper())
        ranked.append(
            RankedFlight(
                flight=flight,
                destination_airport_rank=destination_rank,
                scores=None,
                percent_match=None,
            )
        )

    return ranked


def build_destination_rank_map(ranked_airports: List[RankedAirport]) -> Dict[str, RankedAirport]:
    rank_map: Dict[str, RankedAirport] = {}
    for ranked_airport in ranked_airports:
        rank_map[ranked_airport.airport.iata_code.upper()] = ranked_airport
    return rank_map


def compute_flight_duration_hours(flight: Flight) -> Optional[float]:
    if flight.raw_result.departure.scheduled is None or flight.raw_result.arrival.scheduled is None:
        return None

    try:
        departure_time = datetime.fromisoformat(flight.raw_result.departure.scheduled)
        arrival_time = datetime.fromisoformat(flight.raw_result.arrival.scheduled)
    except ValueError:
        return None

    duration_hours = (arrival_time - departure_time).total_seconds() / 3600.0
    return duration_hours if duration_hours >= 0 else None


def _score_time_against_max(duration_hours: Optional[float], max_flight_time: Optional[int]) -> Optional[float]:
    if max_flight_time is None:
        return None
    if duration_hours is None:
        return 0.0
    if duration_hours <= max_flight_time:
        return 1.0

    decay_rate = 0.5
    return max(0.0, 1 / (1 + ((duration_hours - max_flight_time) * decay_rate)))


def _stable_text_score_seed(value: str) -> int:
    seed = 0
    for index, char in enumerate(value):
        seed += (index + 1) * ord(char)
    return seed


def estimate_flight_cost_usd(flight: Flight, duration_hours: Optional[float]) -> int:
    """Deterministic synthetic ticket-cost estimator used when fare data is unavailable."""
    normalized_duration = duration_hours if duration_hours is not None else 3.5
    route_text = f"{(flight.departure_iata or '').upper()}-{(flight.arrival_iata or '').upper()}"
    carrier_text = (flight.airline_iata or flight.flight_iata or "GEN").upper()

    base_cost = 95 + (normalized_duration * 90)
    route_variance = _stable_text_score_seed(route_text) % 220
    carrier_variance = _stable_text_score_seed(carrier_text) % 110

    synthetic_cost = base_cost + route_variance + carrier_variance
    rounded = int(round(synthetic_cost / 5.0) * 5)
    return max(100, min(2000, rounded))


def _score_cost_against_max(estimated_cost_usd: Optional[int], max_flight_cost: Optional[int]) -> Optional[float]:
    if max_flight_cost is None:
        return None
    if estimated_cost_usd is None:
        return 0.0
    if estimated_cost_usd <= max_flight_cost:
        return 1.0

    decay_rate = 1 / 200.0
    return max(0.0, 1 / (1 + ((estimated_cost_usd - max_flight_cost) * decay_rate)))


def _parse_iso_date(raw: Optional[str]) -> Optional[date]:
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _score_departure_date_alignment(flight_date_raw: Optional[str], desired_departure_raw: Optional[str]) -> Optional[float]:
    if desired_departure_raw is None:
        return None

    flight_date = _parse_iso_date(flight_date_raw)
    desired_departure = _parse_iso_date(desired_departure_raw)
    if flight_date is None or desired_departure is None:
        return 0.0

    day_delta = abs((flight_date - desired_departure).days)
    if day_delta == 0:
        return 1.0
    if day_delta == 1:
        return 0.9
    if day_delta <= 3:
        return 0.75
    if day_delta <= 7:
        return 0.5
    if day_delta <= 14:
        return 0.25
    return 0.0


def _score_flight(flight: Flight, filters: SearchFilters) -> Dict[str, Any]:
    duration_hours = compute_flight_duration_hours(flight)
    estimated_cost_usd = estimate_flight_cost_usd(flight, duration_hours)

    raw_scores: Dict[str, Optional[float]] = {
        "flight_time": _score_time_against_max(duration_hours, filters.max_flight_time),
        "flight_cost": _score_cost_against_max(estimated_cost_usd, filters.max_flight_cost),
        "departure_date": _score_departure_date_alignment(flight.flight_date, filters.departure_date),
    }

    score_values: Dict[str, float] = {
        key: value for key, value in raw_scores.items() if value is not None
    }

    if score_values:
        percent_match = sum(score_values.values()) / len(score_values)
    else:
        # When no flight filters are active, treat all candidate flights as equally valid.
        percent_match = 1.0

    return {
        "flight_iata": flight.flight_iata,
        "flight_number": flight.raw_result.flight.number,
        "flight_callsign": flight.raw_result.flight.icao,
        "airline_iata": flight.airline_iata,
        "airline_name": flight.raw_result.airline.name,
        "flight_status": flight.flight_status,
        "flight_date": flight.flight_date,
        "departure_iata": (flight.departure_iata or "").upper() or None,
        "arrival_iata": (flight.arrival_iata or "").upper() or None,
        "departure_scheduled": flight.raw_result.departure.scheduled,
        "arrival_scheduled": flight.raw_result.arrival.scheduled,
        "duration_hours": round(duration_hours, 2) if duration_hours is not None else None,
        "estimated_cost_usd": estimated_cost_usd,
        "percent_match": round(percent_match, 3),
        "scores": {key: round(value, 3) for key, value in score_values.items()},
    }


def _route_sort_tuple(scored_flight: Dict[str, Any]) -> Tuple[float, float, int]:
    score = scored_flight.get("percent_match")
    duration_hours = scored_flight.get("duration_hours")
    estimated_cost_usd = scored_flight.get("estimated_cost_usd")

    score_value = float(score) if isinstance(score, (int, float)) else -1.0
    duration_value = float(duration_hours) if isinstance(duration_hours, (int, float)) else float("inf")
    cost_value = int(estimated_cost_usd) if isinstance(estimated_cost_usd, int) else 999_999
    return (score_value, -duration_value, -cost_value)


def _round_score(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 3)


def _normalize_airports(codes: Optional[Iterable[str]]) -> List[str]:
    if codes is None:
        return []
    normalized: List[str] = []
    seen: Set[str] = set()
    for code in codes:
        cleaned = (code or "").strip().upper()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _has_airport_preference_filters(filters: SearchFilters) -> bool:
    return bool(
        filters.weather_preferences
        or filters.conditions_preferences
        or filters.geography_preferences
    )


def _fetch_population_map(
    conn: sqlite3.Connection,
    iata_codes: Iterable[str],
) -> Dict[str, Optional[int]]:
    normalized_codes = [code.strip().upper() for code in iata_codes if (code or "").strip()]
    if not normalized_codes:
        return {}

    placeholders = ", ".join(["?"] * len(normalized_codes))
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT UPPER(TRIM(iata_code)) AS iata_code, population
        FROM airport_data
        WHERE UPPER(TRIM(iata_code)) IN ({placeholders})
        """,
        tuple(normalized_codes),
    )

    population_map: Dict[str, Optional[int]] = {}
    for iata_code, population in cursor.fetchall():
        population_map[str(iata_code).upper()] = int(population) if isinstance(population, (int, float)) else None
    return population_map


def _compute_popularity_score(population: Optional[int]) -> Optional[float]:
    if population is None or population <= 0:
        return None
    if population >= URBAN_GEOGRAPHY_POPULATION_SOFT_CAP:
        return 1.0
    return max(0.0, math.log1p(population) / math.log1p(URBAN_GEOGRAPHY_POPULATION_SOFT_CAP))


def _prepare_destination_airports(
    airport_ranked: List[RankedAirport],
    filters: SearchFilters,
    conn: sqlite3.Connection,
) -> Dict[str, Any]:
    if _has_airport_preference_filters(filters):
        return {
            "mode": "filtered",
            "ranked_airports": airport_ranked,
            "display_score_map": {},
            "population_map": {},
        }

    population_map = _fetch_population_map(
        conn,
        [ranked_airport.airport.iata_code for ranked_airport in airport_ranked],
    )

    enriched: List[Tuple[int, float, str, RankedAirport]] = []
    display_score_map: Dict[str, Optional[float]] = {}
    for ranked_airport in airport_ranked:
        iata_code = ranked_airport.airport.iata_code.upper()
        population = population_map.get(iata_code)
        popularity_score = _compute_popularity_score(population)
        display_score_map[iata_code] = popularity_score
        enriched.append(
            (
                int(population) if isinstance(population, int) else -1,
                float(popularity_score) if isinstance(popularity_score, (int, float)) else -1.0,
                iata_code,
                ranked_airport,
            )
        )

    enriched.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return {
        "mode": "population_fallback",
        "ranked_airports": [item[3] for item in enriched],
        "display_score_map": display_score_map,
        "population_map": population_map,
    }


def _fetch_airport_metrics(
    conn: sqlite3.Connection,
    iata_code: str,
) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            weather_temperature_yearly_average,
            weather_sun_yearly_average,
            weather_precip_yearly_average,
            weather_humidity_yearly_average,
            coastal_distance,
            beach_distance,
            population,
            relief_value,
            stddev_value
        FROM airport_data
        WHERE iata_code = ?
        """,
        (iata_code,),
    )
    row = cursor.fetchone()
    if row is None:
        return None

    return {
        "weather_temperature_yearly_average": row[0],
        "weather_sun_yearly_average": row[1],
        "weather_precip_yearly_average": row[2],
        "weather_humidity_yearly_average": row[3],
        "coastal_distance": row[4],
        "beach_distance": row[5],
        "population": row[6],
        "relief_value": row[7],
        "stddev_value": row[8],
    }


def _format_metric(value: Any, unit: str = "", digits: int = 1, thousands: bool = False) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            formatted = f"{value:,.{digits}f}" if thousands else f"{value:.{digits}f}"
        else:
            formatted = f"{value:,d}" if thousands else str(value)
        return f"{formatted}{unit}" if unit else formatted
    return str(value)


def _build_temperature_target(weather_preferences: Optional[List[str]]) -> str:
    prefs = [item for item in (weather_preferences or []) if item in TEMPERATURE_BANDS]
    if not prefs:
        return "Any"

    lowers = [TEMPERATURE_BANDS[item][0] for item in prefs]
    uppers = [TEMPERATURE_BANDS[item][1] for item in prefs]
    low_bound = min(lowers)
    high_bound = max(uppers)
    tags = "/".join(item.capitalize() for item in prefs)
    return f"{low_bound:.1f}ºC to {high_bound:.1f}ºC ({tags})"


def _build_airport_breakdown(
    airport_scores: Dict[str, float],
    airport_metrics: Optional[Dict[str, Any]],
    filters: SearchFilters,
) -> List[Dict[str, Any]]:
    if airport_metrics is None:
        return []

    breakdown: List[Dict[str, Any]] = []

    def add_item(score_key: str, label: str, actual: str, target: str):
        if score_key not in airport_scores:
            return
        score_value = airport_scores.get(score_key)
        breakdown.append(
            {
                "key": score_key,
                "label": label,
                "actual": actual,
                "target": target,
                "score": round(float(score_value), 3) if isinstance(score_value, (int, float)) else None,
            }
        )

    add_item(
        "temperature",
        "Temperature",
        _format_metric(airport_metrics.get("weather_temperature_yearly_average"), "ºC"),
        _build_temperature_target(filters.weather_preferences),
    )
    add_item(
        "sunny",
        "Sun Hours",
        _format_metric(airport_metrics.get("weather_sun_yearly_average"), "h/day"),
        f"≥ {SUNNDY_WEATHER_SUNNY_THRESHOLD:.1f}h/day",
    )
    add_item(
        "dry",
        "Precipitation",
        _format_metric(airport_metrics.get("weather_precip_yearly_average"), "mm/day"),
        f"≤ {DRY_WEATHER_PRECIP_THRESHOLD:.1f}mm/day (Dry)",
    )
    add_item(
        "wet",
        "Precipitation",
        _format_metric(airport_metrics.get("weather_precip_yearly_average"), "mm/day"),
        f"≥ {WET_WEATHER_PRECIP_THRESHOLD:.1f}mm/day (Wet)",
    )
    add_item(
        "dry/wet",
        "Precipitation",
        _format_metric(airport_metrics.get("weather_precip_yearly_average"), "mm/day"),
        (
            f"≤ {DRY_WEATHER_PRECIP_THRESHOLD:.1f}mm/day or "
            f"≥ {WET_WEATHER_PRECIP_THRESHOLD:.1f}mm/day (Dry/Wet)"
        ),
    )
    add_item(
        "low humidity",
        "Humidity",
        _format_metric(airport_metrics.get("weather_humidity_yearly_average"), "%"),
        f"≤ {LOW_HUMIDITY_THRESHOLD:.0f}% (Low Humidity)",
    )
    add_item(
        "high humidity",
        "Humidity",
        _format_metric(airport_metrics.get("weather_humidity_yearly_average"), "%"),
        f"≥ {HIGH_HUMIDITY_THRESHOLD:.0f}% (High Humidity)",
    )
    add_item(
        "low/high humidity",
        "Humidity",
        _format_metric(airport_metrics.get("weather_humidity_yearly_average"), "%"),
        (
            f"≤ {LOW_HUMIDITY_THRESHOLD:.0f}% or "
            f"≥ {HIGH_HUMIDITY_THRESHOLD:.0f}% (Low/High Humidity)"
        ),
    )
    add_item(
        "coastal",
        "Coastal",
        _format_metric(airport_metrics.get("coastal_distance"), " mi"),
        f"≤ {COSTAL_GEOGRAPHY_PROXIMITY_THRESHOLD:.0f} mi to coast",
    )
    add_item(
        "beach",
        "Beach",
        _format_metric(airport_metrics.get("beach_distance"), " mi"),
        f"≤ {BEACH_GEOGRAPHY_PROXIMITY_THRESHOLD:.0f} mi to beach",
    )
    add_item(
        "urban",
        "Urban",
        _format_metric(airport_metrics.get("population"), thousands=True) + " people",
        f"≥ {URBAN_GEOGRAPHY_POPULATION_SOFT_CAP:,} people",
    )

    if "mountainous" in airport_scores:
        actual_relief = _format_metric(airport_metrics.get("relief_value"), "m")
        actual_stddev = _format_metric(airport_metrics.get("stddev_value"), "m")
        score_value = airport_scores.get("mountainous")
        breakdown.append(
            {
                "key": "mountainous",
                "label": "Mountainous Terrain",
                "actual": f"Relief {actual_relief}, Ruggedness {actual_stddev}",
                "target": (
                    f"Relief ≥ {MOUNTAIN_GEOGRAPHY_ELEVATION_THRESHOLD:.0f}m and "
                    f"Ruggedness ≥ {MOUNTAIN_GEOGRAPHY_ELEVATION_SD_THRESHOLD:.0f}m"
                ),
                "score": round(float(score_value), 3) if isinstance(score_value, (int, float)) else None,
            }
        )

    return breakdown


def _index_flights_by_route(flights: List[Flight]) -> Dict[Tuple[str, str], List[Flight]]:
    routes: Dict[Tuple[str, str], List[Flight]] = {}
    for flight in flights:
        departure = (flight.departure_iata or "").strip().upper()
        arrival = (flight.arrival_iata or "").strip().upper()
        if not departure or not arrival:
            continue
        key = (departure, arrival)
        routes.setdefault(key, []).append(flight)
    return routes


def _rank_route_flights(route_flights: List[Flight], filters: SearchFilters) -> List[Dict[str, Any]]:
    scored_options = [_score_flight(flight, filters) for flight in route_flights]
    scored_options.sort(key=_route_sort_tuple, reverse=True)

    for rank_index, option in enumerate(scored_options, start=1):
        option["rank"] = rank_index
    return scored_options


def build_combined_destination_rankings(
    airport_ranked: List[RankedAirport],
    filters: SearchFilters,
    api_key: str,
    destination_candidate_limit: int = MAX_DESTINATION_CANDIDATES,
) -> Dict[str, Any]:
    origin_airports = _normalize_airports(filters.airports)
    ordered_origin_airports = sorted(origin_airports)
    if not ordered_origin_airports:
        raise FlightApiInputError("Please select at least one origin airport before optimizing travel.")
    if not filters.departure_date or not filters.return_date:
        raise FlightApiInputError(
            "Departure and return dates are required to optimize travel."
        )

    destination_rows: List[Dict[str, Any]] = []
    excluded_destinations: List[Dict[str, Any]] = []
    skipped_origin_destinations: List[str] = []
    active_flight_score_keys: Set[str] = set()
    considered_destinations: List[str] = []
    loaded_route_flights: List[Flight] = []
    route_options_cache: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    route_errors: List[Dict[str, str]] = []
    provider_diagnostics: Dict[str, Any] = {"provider": "flightapi"}
    provider_warnings: List[str] = []

    target_destination_count = max(1, destination_candidate_limit)
    minimum_destination_results = MIN_COMBINED_RESULTS_TARGET
    airport_conn = sqlite3.connect(DB_PATH)

    try:
        destination_preparation = _prepare_destination_airports(airport_ranked, filters, airport_conn)
        all_ranked_destination_airports = destination_preparation["ranked_airports"]
        airport_ranking_mode = str(destination_preparation["mode"])
        airport_display_score_map: Dict[str, Optional[float]] = destination_preparation["display_score_map"]
        ranked_destination_airports = [
            ranked_airport
            for ranked_airport in all_ranked_destination_airports
            if ranked_airport.airport.iata_code.upper() not in origin_airports
        ]
        top_destination_candidates = ranked_destination_airports[:target_destination_count]
        initial_top_candidates = [
            ranked_airport.airport.iata_code.upper()
            for ranked_airport in top_destination_candidates
        ]

        logger.info(
            "airport-ranking:complete airport_mode=%s target_results=%s initial_top_candidates=%s total_ranked_destinations=%s",
            airport_ranking_mode,
            target_destination_count,
            initial_top_candidates,
            len(ranked_destination_airports),
        )

        airport_rank_map = {
            ranked_airport.airport.iata_code.upper(): index
            for index, ranked_airport in enumerate(ranked_destination_airports, start=1)
        }

        with FlightApiClient(api_key=api_key) as flight_api_client:
            # Start with top N candidates, then continue down the ranked list until
            # we have enough shared destinations or we run out of airports.
            for ranked_airport in ranked_destination_airports:
                destination_iata = ranked_airport.airport.iata_code.upper()
                considered_destinations.append(destination_iata)
                logger.info(
                    "destination:consider iata=%s airport_mode=%s airport_rank=%s",
                    destination_iata,
                    airport_ranking_mode,
                    airport_rank_map.get(destination_iata),
                )

                missing_origins: List[str] = []
                selected_flights: List[Dict[str, Any]] = []

                for origin_index, origin_iata in enumerate(ordered_origin_airports, start=1):
                    route_key = (origin_iata, destination_iata)
                    if route_key not in route_options_cache:
                        try:
                            route_flights = flight_api_client.load_route_flights(
                                origin_iata=origin_iata,
                                destination_iata=destination_iata,
                                departure_date=filters.departure_date or "",
                            )
                        except FlightApiError as exc:
                            warning = (
                                f"Route lookup failed for {origin_iata}->{destination_iata}: {exc}"
                            )
                            provider_warnings.append(warning)
                            route_errors.append(
                                {
                                    "origin_iata": origin_iata,
                                    "destination_iata": destination_iata,
                                    "error": str(exc),
                                }
                            )
                            logger.warning(
                                "destination:route-error destination=%s origin=%s error=%s",
                                destination_iata,
                                origin_iata,
                                exc,
                            )
                            route_flights = []
                        loaded_route_flights.extend(route_flights)
                        route_options_cache[route_key] = _rank_route_flights(route_flights, filters)

                    route_options = route_options_cache[route_key]
                    if not route_options:
                        missing_origins.append(origin_iata)
                        logger.info(
                            "destination:missing-origin destination=%s origin=%s",
                            destination_iata,
                            origin_iata,
                        )
                        break

                    selected_option = dict(route_options[0])
                    selected_option["option_count"] = len(route_options)
                    selected_option["origin_slot"] = origin_index
                    selected_flights.append(selected_option)
                    active_flight_score_keys.update(selected_option["scores"].keys())

                if ordered_origin_airports and missing_origins:
                    excluded_destinations.append(
                        {
                            "destination_iata": destination_iata,
                            "missing_origins": missing_origins,
                        }
                    )
                    logger.info(
                        "destination:excluded destination=%s missing_origins=%s",
                        destination_iata,
                        missing_origins,
                    )
                    continue

                # Keep flight rows in alphabetical-origin order so each traveler appears
                # in a stable position across all destination cards.
                selected_flights.sort(
                    key=lambda item: (str(item.get("departure_iata") or ""), int(item.get("origin_slot", 999_999)))
                )
                for flight_rank, flight_row in enumerate(selected_flights, start=1):
                    flight_row["flight_rank"] = flight_rank

                airport_score = (
                    ranked_airport.percent_match
                    if airport_ranking_mode == "filtered"
                    else airport_display_score_map.get(destination_iata)
                )
                flight_scores = [
                    float(item["percent_match"])
                    for item in selected_flights
                    if isinstance(item.get("percent_match"), (float, int))
                ]
                flight_score = (sum(flight_scores) / len(flight_scores)) if flight_scores else None
                combined_price_usd = (
                    sum(
                        int(item["estimated_cost_usd"])
                        for item in selected_flights
                        if isinstance(item.get("estimated_cost_usd"), int)
                    )
                    if selected_flights
                    else None
                )

                score_inputs = [
                    score
                    for score in (
                        airport_score if airport_ranking_mode == "filtered" else None,
                        flight_score,
                    )
                    if score is not None
                ]
                combined_score = (sum(score_inputs) / len(score_inputs)) if score_inputs else None

                airport_scores = ranked_airport.scores or {}
                airport_metrics = _fetch_airport_metrics(airport_conn, destination_iata)
                airport_breakdown = _build_airport_breakdown(airport_scores, airport_metrics, filters)

                destination_rows.append(
                    {
                        "destination_iata": destination_iata,
                        "destination_name": ranked_airport.airport.name,
                        "airport_rank": airport_rank_map.get(destination_iata),
                        "airport_score": _round_score(airport_score),
                        "airport_scores": airport_scores,
                        "airport_breakdown": airport_breakdown,
                        "flight_score": _round_score(flight_score),
                        "combined_score": _round_score(combined_score),
                        "combined_price_usd": combined_price_usd,
                        "flights": selected_flights,
                    }
                )
                logger.info(
                    "destination:accepted destination=%s airport_score=%s flight_score=%s combined_score=%s flights=%s",
                    destination_iata,
                    _round_score(airport_score),
                    _round_score(flight_score),
                    _round_score(combined_score),
                    len(selected_flights),
                )
                # Always inspect at least the first top-N candidates. After that,
                # stop once we have a healthy number of shared destinations.
                if len(considered_destinations) >= target_destination_count and len(destination_rows) >= minimum_destination_results:
                    break
            provider_diagnostics = dict(flight_api_client.diagnostics)
            provider_warnings = list(
                dict.fromkeys([*provider_warnings, *flight_api_client.warnings])
            )
    finally:
        airport_conn.close()

    destination_rows.sort(
        key=lambda row: (
            float(row["combined_score"]) if isinstance(row.get("combined_score"), (int, float)) else -1.0,
            float(row["flight_score"]) if isinstance(row.get("flight_score"), (int, float)) else -1.0,
            float(row["airport_score"]) if isinstance(row.get("airport_score"), (int, float)) else -1.0,
        ),
        reverse=True,
    )
    for rank_index, row in enumerate(destination_rows, start=1):
        row["rank"] = rank_index

    flight_ranked_rows = sorted(
        [row for row in destination_rows if isinstance(row.get("flight_score"), (int, float))],
        key=lambda row: float(row["flight_score"]),
        reverse=True,
    )
    for flight_rank, row in enumerate(flight_ranked_rows, start=1):
        row["flight_rank"] = flight_rank
    for row in destination_rows:
        row.setdefault("flight_rank", None)

    message: Optional[str] = None
    if ordered_origin_airports and not destination_rows:
        message = "There isn't an airport that has all selected origin airports in common."
    elif provider_warnings:
        message = provider_warnings[0]

    logger.info(
        "combined-ranking:complete results=%s excluded=%s skipped_self=%s considered=%s message=%s",
        len(destination_rows),
        len(excluded_destinations),
        len(skipped_origin_destinations),
        len(considered_destinations),
        message,
    )

    return {
        "results": destination_rows,
        "active_flight_score_keys": sorted(active_flight_score_keys),
        "diagnostics": {
            "candidate_destination_limit": target_destination_count,
            "initial_top_ranked_airport_candidates": initial_top_candidates,
            "candidate_destinations_considered": considered_destinations,
            "selected_origin_airports": origin_airports,
            "ordered_origin_airports": ordered_origin_airports,
            "airport_ranking_mode": airport_ranking_mode,
            "skipped_origin_destinations": skipped_origin_destinations,
            "excluded_destinations_missing_origins": excluded_destinations,
            "flight_data_source": "flightapi",
            "flight_price_source": "estimated",
            "flight_price_note": (
                "The connected FlightAPI tracking endpoints do not include ticket fares, "
                "so cost-based ranking still uses the local estimator."
            ),
            "live_flights_loaded": len(loaded_route_flights),
            "provider": provider_diagnostics,
            "provider_warnings": provider_warnings,
            "route_errors": route_errors,
            "flight_filter_context": {
                "max_flight_time": filters.max_flight_time,
                "max_flight_cost": filters.max_flight_cost,
                "departure_date": filters.departure_date,
                "return_date": filters.return_date,
            },
            "return_date": filters.return_date,
        },
        "message": message,
    }


# ======================================
# ======== RANKING FUNCTIONS ===========
# ======================================

def rank_logistic_flight_time(flights: List[RankedFlight], filters: SearchFilters) -> List[RankedFlight]:
    ranked: List[RankedFlight] = []

    if filters.max_flight_time is None:
        return flights

    for ranked_flight in flights:
        flight_time_score = 0.0
        flight_duration_hours = compute_flight_duration_hours(ranked_flight.flight)

        if flight_duration_hours is not None:
            if flight_duration_hours <= filters.max_flight_time:
                flight_time_score = 1.0
            else:
                decay_rate = 0.5
                flight_time_score = 1 / (1 + ((flight_duration_hours - filters.max_flight_time) * decay_rate))
                flight_time_score = max(flight_time_score, 0.0)

        ranked.append(_append_flight_score(ranked_flight, "flight_time", flight_time_score))

    return ranked


def run_all_flight_ranks(flights: List[RankedFlight], filters: SearchFilters) -> List[RankedFlight]:
    ranked = rank_logistic_flight_time(flights, filters)
    return ranked


def overall_flight_rank(flights: List[RankedFlight], filters: SearchFilters) -> FlightRankResult:
    ranked: List[RankedFlight] = []
    active_score_keys: Set[str] = set()

    for ranked_flight in flights:
        if ranked_flight.scores is None:
            ranked.append(ranked_flight)
            continue

        total_score = 0.0
        count = 0
        for key, value in ranked_flight.scores.items():
            total_score += value
            count += 1
            active_score_keys.add(key)

        percent_match = (total_score / count) if count > 0 else None
        ranked.append(
            RankedFlight(
                flight=ranked_flight.flight,
                destination_airport_rank=ranked_flight.destination_airport_rank,
                scores=ranked_flight.scores,
                percent_match=percent_match,
            )
        )

    ranked.sort(key=lambda x: (x.percent_match if x.percent_match is not None else -1), reverse=True)
    return FlightRankResult(ranked=ranked, active_score_keys=list(active_score_keys))


def format_flight_rank_results(rank_result: FlightRankResult, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    ranked = rank_result.ranked if limit is None else rank_result.ranked[:limit]
    formatted_results: List[Dict[str, Any]] = []

    for idx, ranked_flight in enumerate(ranked, start=1):
        formatted_results.append(
            {
                "rank": idx,
                "flight_iata": ranked_flight.flight.flight_iata,
                "departure_iata": ranked_flight.flight.departure_iata,
                "arrival_iata": ranked_flight.flight.arrival_iata,
                "airline_iata": ranked_flight.flight.airline_iata,
                "percent_match": round(ranked_flight.percent_match, 3)
                if ranked_flight.percent_match is not None
                else None,
                "scores": ranked_flight.scores,
            }
        )

    return formatted_results
