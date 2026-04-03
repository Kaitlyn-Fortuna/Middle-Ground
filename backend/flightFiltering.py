from __future__ import annotations

# ============================
# ======== IMPORTS ===========
# ============================

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from datetime import date, datetime

from parseResults import (
    Flight,
    load_flights_dataset_json,
)
from parseFilters import (
    SearchFilters,
    load_filters_json,
    parse_filters_json,
)
from airportFiltering import (
    RankedAirport,
    import_airport_data,
    initialize_ranked_airports,
    overall_rank,
    run_all_ranks,
)
from models import (
    FlightRankResult, 
    RankedFlight
)


# ====================================
# ======== SCORING CONSTANTS =========
# ====================================

FAKE_RESULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "results-test.json"
MAX_DESTINATION_CANDIDATES = 5



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
    """Deterministic synthetic ticket-cost estimator used for local fake-data ranking."""
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
        "airline_iata": flight.airline_iata,
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


def _build_no_flight_required_option(
    origin_iata: str,
    destination_iata: str,
    filters: SearchFilters,
) -> Dict[str, Any]:
    scores: Dict[str, float] = {}
    if filters.max_flight_time is not None:
        scores["flight_time"] = 1.0
    if filters.max_flight_cost is not None:
        scores["flight_cost"] = 1.0
    if filters.departure_date is not None:
        scores["departure_date"] = 1.0

    return {
        "rank": 1,
        "flight_iata": "NO-FLIGHT",
        "airline_iata": None,
        "flight_status": "not_required",
        "flight_date": None,
        "departure_iata": origin_iata,
        "arrival_iata": destination_iata,
        "departure_scheduled": None,
        "arrival_scheduled": None,
        "duration_hours": 0.0,
        "estimated_cost_usd": 0,
        "percent_match": 1.0,
        "scores": scores,
    }


def _rank_route_flights(route_flights: List[Flight], filters: SearchFilters) -> List[Dict[str, Any]]:
    scored_options = [_score_flight(flight, filters) for flight in route_flights]
    scored_options.sort(key=_route_sort_tuple, reverse=True)

    for rank_index, option in enumerate(scored_options, start=1):
        option["rank"] = rank_index
    return scored_options


def build_combined_destination_rankings(
    airport_ranked: List[RankedAirport],
    filters: SearchFilters,
    destination_candidate_limit: int = MAX_DESTINATION_CANDIDATES,
) -> Dict[str, Any]:
    origin_airports = _normalize_airports(filters.airports)
    route_flights = load_flights_dataset_json(FAKE_RESULTS_PATH)
    flights_by_route = _index_flights_by_route(route_flights)

    destination_rows: List[Dict[str, Any]] = []
    excluded_destinations: List[Dict[str, Any]] = []
    active_flight_score_keys: Set[str] = set()
    considered_destinations: List[str] = []

    airport_rank_map = {
        ranked_airport.airport.iata_code.upper(): index
        for index, ranked_airport in enumerate(airport_ranked, start=1)
    }
    target_destination_count = max(1, destination_candidate_limit)

    for ranked_airport in airport_ranked:
        destination_iata = ranked_airport.airport.iata_code.upper()
        considered_destinations.append(destination_iata)

        missing_origins: List[str] = []
        selected_flights: List[Dict[str, Any]] = []

        for origin_iata in origin_airports:
            if origin_iata == destination_iata:
                selected_option = _build_no_flight_required_option(origin_iata, destination_iata, filters)
                selected_flights.append(selected_option)
                active_flight_score_keys.update(selected_option["scores"].keys())
                continue

            route_key = (origin_iata, destination_iata)
            route_options = _rank_route_flights(flights_by_route.get(route_key, []), filters)
            if not route_options:
                missing_origins.append(origin_iata)
                continue

            selected_option = dict(route_options[0])
            selected_option["option_count"] = len(route_options)
            selected_flights.append(selected_option)
            active_flight_score_keys.update(selected_option["scores"].keys())

        if origin_airports and missing_origins:
            excluded_destinations.append(
                {
                    "destination_iata": destination_iata,
                    "missing_origins": missing_origins,
                }
            )
            continue

        selected_flights.sort(
            key=lambda item: (
                float(item.get("percent_match", -1)),
                -(
                    float(item["duration_hours"])
                    if isinstance(item.get("duration_hours"), (int, float))
                    else float("inf")
                ),
                -(
                    int(item["estimated_cost_usd"])
                    if isinstance(item.get("estimated_cost_usd"), int)
                    else 999_999
                ),
            ),
            reverse=True,
        )
        for flight_rank, flight_row in enumerate(selected_flights, start=1):
            flight_row["flight_rank"] = flight_rank

        airport_score = ranked_airport.percent_match
        flight_scores = [
            float(item["percent_match"])
            for item in selected_flights
            if isinstance(item.get("percent_match"), (float, int))
        ]
        flight_score = (sum(flight_scores) / len(flight_scores)) if flight_scores else None

        score_inputs = [score for score in (airport_score, flight_score) if score is not None]
        combined_score = (sum(score_inputs) / len(score_inputs)) if score_inputs else None

        destination_rows.append(
            {
                "destination_iata": destination_iata,
                "destination_name": ranked_airport.airport.name,
                "airport_rank": airport_rank_map.get(destination_iata),
                "airport_score": _round_score(airport_score),
                "airport_scores": ranked_airport.scores or {},
                "flight_score": _round_score(flight_score),
                "combined_score": _round_score(combined_score),
                "flights": selected_flights,
            }
        )
        if len(destination_rows) >= target_destination_count:
            break

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
    if origin_airports and not destination_rows:
        message = (
            "No ranked destination had flights from every selected origin airport "
            "in the local fake dataset."
        )
    elif not origin_airports:
        message = (
            "No origin airports selected, so this ranking reflects airport filters only. "
            "Flight scoring is applied after origin airports are selected."
        )

    return {
        "results": destination_rows,
        "active_flight_score_keys": sorted(active_flight_score_keys),
        "diagnostics": {
            "candidate_destination_limit": target_destination_count,
            "candidate_destinations_considered": considered_destinations,
            "selected_origin_airports": origin_airports,
            "excluded_destinations_missing_origins": excluded_destinations,
            "fake_flights_loaded": len(route_flights),
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


# =======================================
# =========== LOCAL TESTING =============
# =======================================

if __name__ == "__main__":
    filters_path = Path("data/filters-test.json")
    filters_data = load_filters_json(filters_path)
    parsed_filters = parse_filters_json(filters_data)

    results_path = Path("data/results-test.json")
    flights = load_flights_dataset_json(results_path)

    ranked_flights = initialize_ranked_flights(flights)
    ranked_flights = run_all_flight_ranks(ranked_flights, parsed_filters)

    final_rank = overall_flight_rank(ranked_flights, parsed_filters)
    print(f"Final overall rank of {len(final_rank.ranked)} flights:")
    for idx, ranked in enumerate(final_rank.ranked[:25], start=1):  # Print the first 25 ranked airports
        percent_text = f"{ranked.percent_match:.3f}" if ranked.percent_match is not None else "N/A"
        print(f"{idx} | {ranked.flight.flight_iata} | {ranked.flight.departure_iata} | {ranked.flight.arrival_iata} | {percent_text}")
