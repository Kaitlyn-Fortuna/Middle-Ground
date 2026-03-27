from __future__ import annotations

# ============================
# ======== IMPORTS ===========
# ============================

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

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



# =======================================
# =========== LOCAL TESTING =============
# =======================================


