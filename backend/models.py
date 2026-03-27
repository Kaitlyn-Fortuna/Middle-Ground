from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================
# ======== AIRPORTS ==========
# ============================

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


# ============================
# ======== FLIGHTS ===========
# ============================

@dataclass(frozen=True)
class FlightEndpoint:
    airport: Optional[str] = None
    timezone: Optional[str] = None
    iata: Optional[str] = None
    icao: Optional[str] = None
    terminal: Optional[str] = None
    gate: Optional[str] = None
    baggage: Optional[str] = None
    delay: Optional[int] = None
    scheduled: Optional[str] = None
    estimated: Optional[str] = None
    actual: Optional[str] = None
    estimated_runway: Optional[str] = None
    actual_runway: Optional[str] = None


@dataclass(frozen=True)
class AirlineInfo:
    name: Optional[str] = None
    iata: Optional[str] = None
    icao: Optional[str] = None


@dataclass(frozen=True)
class FlightInfo:
    number: Optional[str] = None
    iata: Optional[str] = None
    icao: Optional[str] = None
    codeshared: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class FlightResult:
    flight_date: Optional[str] = None
    flight_status: Optional[str] = None
    departure: FlightEndpoint = field(default_factory=FlightEndpoint)
    arrival: FlightEndpoint = field(default_factory=FlightEndpoint)
    airline: AirlineInfo = field(default_factory=AirlineInfo)
    flight: FlightInfo = field(default_factory=FlightInfo)
    aircraft: Optional[Dict[str, Any]] = None
    live: Optional[Dict[str, Any]] = None


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
