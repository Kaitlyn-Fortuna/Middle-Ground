from __future__ import annotations

# ============================
# ======== IMPORTS ===========
# ============================

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

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


# ================================
# ======== DATA MODELS ===========
# ================================

@dataclass(frozen=True)
class RankedFlight:
    flight: Flight
    destination_airport_rank: Optional[RankedAirport]
    scores: Optional[Dict[str, float]]
    percent_match: Optional[float]


@dataclass(frozen=True)
class FlightRankResult:
    ranked: List[RankedFlight]
    active_score_keys: List[str]
    diagnostics: Dict[str, object] = field(default_factory=dict)


# ====================================
# ======== SCORING CONSTANTS =========
# ====================================



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


# ======================================
# ======== RANKING FUNCTIONS ===========
# ======================================

def rank_logistic_flight_time(flights: List[RankedFlight], filters: SearchFilters) -> List[RankedFlight]:
    ranked: List[RankedFlight] = []

    if filters.max_flight_time is None:
        return flights

    for ranked_flight in flights:
        flight_time_score = 0.0
        if ranked_flight.flight.raw_result.departure.scheduled and ranked_flight.flight.raw_result.arrival.scheduled:

            try:
                departure_time = datetime.fromisoformat(ranked_flight.flight.raw_result.departure.scheduled)
                arrival_time = datetime.fromisoformat(ranked_flight.flight.raw_result.arrival.scheduled)
                flight_duration_hours = (arrival_time - departure_time).total_seconds() / 3600.0

                if flight_duration_hours <= filters.max_flight_time:
                    flight_time_score = 1.0
                else:
                    decay_rate = 0.5
                    flight_time_score = 1 / (1 + ((flight_duration_hours - filters.max_flight_time) * decay_rate))
                    flight_time_score = max(flight_time_score, 0.0)

            except Exception:
                flight_time_score = 0.0

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
    for ranked in final_rank.ranked[:25]:  # Print the first 25 ranked flights
        print(ranked.flight.flight_iata, ranked.flight.departure_iata, ranked.flight.arrival_iata, ranked.percent_match)

    print(json.dumps(format_flight_rank_results(final_rank, limit=25), indent=2))
