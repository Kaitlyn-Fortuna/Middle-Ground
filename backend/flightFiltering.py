from __future__ import annotations

# ============================
# ======== IMPORTS ===========
# ============================

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set
from datetime import datetime

from parseResults import (
    FlightResult,
    load_results_json,
    parse_results_json,
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
class Flight:
    raw_result: FlightResult
    departure_iata: Optional[str]
    arrival_iata: Optional[str]
    flight_date: Optional[str]
    flight_status: Optional[str]
    flight_iata: Optional[str]
    airline_iata: Optional[str]


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


def normalize_results_to_flights(results: Sequence[FlightResult]) -> List[Flight]:
    flights: List[Flight] = []
    for result in results:
        flights.append(
            Flight(
                raw_result=result,
                departure_iata=result.departure.iata,
                arrival_iata=result.arrival.iata,
                flight_date=result.flight_date,
                flight_status=result.flight_status,
                flight_iata=result.flight.iata,
                airline_iata=result.airline.iata,
            )
        )
    return flights


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


# =======================================
# =========== LOCAL TESTING =============
# =======================================

if __name__ == "__main__":
    filters_path = Path("data/filters-test.json")
    filters_data = load_filters_json(filters_path)
    parsed_filters = parse_filters_json(filters_data)

    results_path = Path("data/results-test.json")
    results_data = load_results_json(results_path)
    parsed_results = parse_results_json(results_data)

    flights = normalize_results_to_flights([parsed_results])

    ranked_flights = initialize_ranked_flights(flights)
    ranked_flights = rank_logistic_flight_time(ranked_flights, parsed_filters)

    print(f"Ranked {len(ranked_flights)} flights by flight time:")
    for ranked in ranked_flights[:25]:  # Print the first 25 ranked flights
        print(ranked.flight.flight_iata, ranked.flight.departure_iata, ranked.flight.arrival_iata, ranked.scores)