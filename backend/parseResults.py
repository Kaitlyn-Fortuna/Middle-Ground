from __future__ import annotations

# ============================
# ======== IMPORTS ===========
# ============================

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
from dataclasses import dataclass, field


# ================================
# ======== DATA MODELS ===========
# ================================

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


# ============================
# ======== HELPERS ===========
# ============================

def load_results_json(path: Path) -> Dict[str, Any]:
	with path.open("r", encoding="utf-8") as f:
		return json.load(f)


def _first_present(data: Dict[str, Any], keys: Iterable[str]) -> Any:
	for key in keys:
		if key in data:
			return data[key]
	return None


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


def _parse_optional_str(value: Any) -> Optional[str]:
	if isinstance(value, str):
		cleaned = value.strip()
		return cleaned if cleaned else None
	return None


def _parse_optional_dict(value: Any) -> Optional[Dict[str, Any]]:
	if isinstance(value, dict):
		return value
	return None


def _coerce_results_dataset(payload: Any) -> Sequence[Any]:
	if payload is None:
		return []

	if isinstance(payload, str):
		try:
			payload = json.loads(payload)
		except json.JSONDecodeError:
			return []

	if isinstance(payload, list):
		return payload

	if isinstance(payload, dict):
		data = payload.get("data")
		if isinstance(data, list):
			return data
		return [payload]

	return []


# =====================================
# ======== PARSING FUNCTIONS ==========
# =====================================

def _parse_endpoint(data: Any) -> FlightEndpoint:
	if not isinstance(data, dict):
		return FlightEndpoint()

	return FlightEndpoint(
		airport=_parse_optional_str(_first_present(data, ("airport",))),
		timezone=_parse_optional_str(_first_present(data, ("timezone",))),
		iata=_parse_optional_str(_first_present(data, ("iata",))),
		icao=_parse_optional_str(_first_present(data, ("icao",))),
		terminal=_parse_optional_str(_first_present(data, ("terminal",))),
		gate=_parse_optional_str(_first_present(data, ("gate",))),
		baggage=_parse_optional_str(_first_present(data, ("baggage",))),
		delay=_parse_optional_int(_first_present(data, ("delay",))),
		scheduled=_parse_optional_str(_first_present(data, ("scheduled",))),
		estimated=_parse_optional_str(_first_present(data, ("estimated",))),
		actual=_parse_optional_str(_first_present(data, ("actual",))),
		estimated_runway=_parse_optional_str(_first_present(data, ("estimated_runway",))),
		actual_runway=_parse_optional_str(_first_present(data, ("actual_runway",))),
	)


def _parse_airline(data: Any) -> AirlineInfo:
	if not isinstance(data, dict):
		return AirlineInfo()

	return AirlineInfo(
		name=_parse_optional_str(_first_present(data, ("name",))),
		iata=_parse_optional_str(_first_present(data, ("iata",))),
		icao=_parse_optional_str(_first_present(data, ("icao",))),
	)


def _parse_flight(data: Any) -> FlightInfo:
	if not isinstance(data, dict):
		return FlightInfo()

	return FlightInfo(
		number=_parse_optional_str(_first_present(data, ("number",))),
		iata=_parse_optional_str(_first_present(data, ("iata",))),
		icao=_parse_optional_str(_first_present(data, ("icao",))),
		codeshared=_parse_optional_dict(_first_present(data, ("codeshared",))),
	)


def parse_results_json(data: Dict[str, Any]) -> FlightResult:
	return FlightResult(
		flight_date=_parse_optional_str(_first_present(data, ("flight_date",))),
		flight_status=_parse_optional_str(_first_present(data, ("flight_status",))),
		departure=_parse_endpoint(_first_present(data, ("departure",))),
		arrival=_parse_endpoint(_first_present(data, ("arrival",))),
		airline=_parse_airline(_first_present(data, ("airline",))),
		flight=_parse_flight(_first_present(data, ("flight",))),
		aircraft=_parse_optional_dict(_first_present(data, ("aircraft",))),
		live=_parse_optional_dict(_first_present(data, ("live",))),
	)


def parse_results_api_json(payload: Any) -> FlightResult:
	if payload is None:
		return FlightResult()

	if isinstance(payload, str):
		try:
			payload = json.loads(payload)
		except json.JSONDecodeError:
			return FlightResult()

	if not isinstance(payload, dict):
		return FlightResult()

	return parse_results_json(payload)


def parse_results_dataset_json(payload: Any) -> List[FlightResult]:
	results: List[FlightResult] = []
	for item in _coerce_results_dataset(payload):
		if isinstance(item, dict):
			results.append(parse_results_json(item))
	return results


def parse_results_dataset_api_json(payload: Any) -> List[FlightResult]:
	return parse_results_dataset_json(payload)


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


def load_results_dataset_json(path: Path) -> List[FlightResult]:
	return parse_results_dataset_json(load_results_json(path))


def load_flights_dataset_json(path: Path) -> List[Flight]:
	return normalize_results_to_flights(load_results_dataset_json(path))


# =======================================
# =========== LOCAL TESTING =============
# =======================================

if __name__ == "__main__":
	results_path = Path("data/results-test.json")
	results_data = load_results_json(results_path)
	print(results_data)
	parsed_results = parse_results_json(results_data)
	print(parsed_results)
	parsed_dataset = load_results_dataset_json(results_path)
	print(parsed_dataset)
	normalized_flights = load_flights_dataset_json(results_path)
	print(normalized_flights)
