from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from models import AirlineInfo, Flight, FlightEndpoint, FlightInfo, FlightResult


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DB_PATH = DATA_DIR / "flight_api_cache.db"

TRACK_BY_ROUTE_ENDPOINT = "https://api.flightapi.io/trackbyroute"
FLIGHT_TRACKING_ENDPOINT = "https://api.flightapi.io/airline"
AIRLINE_CODE_ENDPOINT = "https://api.flightapi.io/iata"

ROUTE_CACHE_TTL_HOURS = 12
DETAIL_CACHE_TTL_HOURS = 12
AIRLINE_CODE_CACHE_TTL_DAYS = 30
ROUTE_CACHE_KEY_VERSION = "v2"
DETAIL_CACHE_KEY_VERSION = "v2"
AIRLINE_CACHE_KEY_VERSION = "v1"

logger = logging.getLogger("middleground.flightapi")


class FlightApiError(RuntimeError):
    pass


class FlightApiNoDataError(FlightApiError):
    pass


class FlightApiInputError(ValueError):
    pass


@dataclass
class FlightApiFetchResult:
    flights: List[Flight]
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise FlightApiInputError(f"Invalid date '{raw}'. Expected YYYY-MM-DD.") from exc


def _format_api_date(raw: str) -> str:
    return _parse_iso_date(raw).strftime("%Y%m%d")


def _normalize_iata_codes(values: Optional[Iterable[str]]) -> List[str]:
    if values is None:
        return []

    normalized: List[str] = []
    seen = set()
    for value in values:
        cleaned = (value or "").strip().upper()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _coerce_sequence(payload: Any) -> Sequence[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
        return [payload]
    return []


def _extract_route_flights(payload: Any) -> Sequence[Any]:
    if isinstance(payload, dict):
        flights = payload.get("flights")
        if isinstance(flights, list):
            return flights
    return _coerce_sequence(payload)


def _pick_value(data: Any, *keys: str) -> Any:
    if not isinstance(data, dict):
        return None

    normalized_map = {
        _normalize_key(str(key)): value
        for key, value in data.items()
    }

    for key in keys:
        if key in data:
            return data[key]
        normalized_key = _normalize_key(key)
        if normalized_key in normalized_map:
            return normalized_map[normalized_key]
    return None


def _pick_str(data: Any, *keys: str) -> Optional[str]:
    value = _pick_value(data, *keys)
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _pick_dict(data: Any, *keys: str) -> Optional[Dict[str, Any]]:
    value = _pick_value(data, *keys)
    return value if isinstance(value, dict) else None


def _pick_nested_str(data: Any, path: Tuple[str, ...]) -> Optional[str]:
    current = data
    for key in path:
        current = _pick_value(current, key)
        if current is None:
            return None
    if isinstance(current, str):
        cleaned = current.strip()
        return cleaned or None
    if isinstance(current, (int, float)):
        return str(current)
    return None


def _coalesce(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return None


def _sanitize_flight_number(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = re.sub(r"\s+", "", value)
    match = re.search(r"(\d+[A-Z]?)", cleaned.upper())
    return match.group(1) if match else cleaned.upper()


def _split_operated_by(value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not value:
        return (None, None)

    cleaned = " ".join(value.split())
    match = re.match(r"^(.*?)(\d+[A-Z]?)$", cleaned)
    if not match:
        return (cleaned, None)
    airline_name = match.group(1).strip() or None
    flight_number = match.group(2).strip() or None
    return (airline_name, flight_number)


def _parse_route_datetime(raw_value: Optional[str], base_date: str) -> Optional[str]:
    if not raw_value:
        return None

    day = _parse_iso_date(base_date)
    cleaned = " ".join(raw_value.replace(".", "").split())
    formats = (
        "%I:%M %p, %b %d",
        "%I:%M %p, %B %d",
        "%H:%M, %b %d",
        "%H:%M, %B %d",
    )

    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(year=day.year).isoformat()
        except ValueError:
            continue
    return None


def _parse_detail_datetime(endpoint_data: Any, *keys: str) -> Optional[str]:
    for key in keys:
        raw_value = _pick_str(endpoint_data, key)
        if not raw_value:
            continue
        try:
            parsed = datetime.fromisoformat(raw_value)
            return parsed.isoformat()
        except ValueError:
            continue
    return None


def _extract_tracking_bundle(payload: Any) -> Dict[str, Any]:
    bundle: Dict[str, Any] = {}
    for item in _coerce_sequence(payload):
        if not isinstance(item, dict):
            continue
        for field_name in ("departure", "arrival", "airline", "flight", "status"):
            value = _pick_value(item, field_name)
            if value is not None and field_name not in bundle:
                bundle[field_name] = value
    return bundle


def _extract_error_message(raw_body: str) -> Optional[str]:
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return None

    message = payload.get("message") if isinstance(payload, dict) else None
    if isinstance(message, str):
        cleaned = message.strip()
        return cleaned or None
    return None


def _is_no_data_message(message: Optional[str]) -> bool:
    if not message:
        return False
    normalized = " ".join(message.lower().split())
    return normalized == "no details for your input"


class FlightApiClient:
    def __init__(self, api_key: str, cache_db_path: Path = CACHE_DB_PATH):
        cleaned_key = (api_key or "").strip()
        if not cleaned_key:
            raise FlightApiInputError("Missing FlightAPI key.")

        self.api_key = cleaned_key
        self.cache_db_path = cache_db_path
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.cache_db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_cache_tables()
        self.diagnostics: Dict[str, Any] = {
            "provider": "flightapi",
            "cache_db_path": str(self.cache_db_path),
            "route_requests": 0,
            "route_cache_hits": 0,
            "route_stale_hits": 0,
            "route_no_data": 0,
            "detail_requests": 0,
            "detail_cache_hits": 0,
            "detail_stale_hits": 0,
            "detail_no_data": 0,
            "airline_code_requests": 0,
            "airline_code_cache_hits": 0,
            "airline_code_stale_hits": 0,
            "route_pairs_requested": [],
            "detail_lookups_attempted": 0,
            "detail_lookups_succeeded": 0,
            "detail_lookups_failed": 0,
        }
        self.warnings: List[str] = []

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "FlightApiClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _ensure_cache_tables(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS route_cache (
                cache_key TEXT PRIMARY KEY,
                origin_iata TEXT NOT NULL,
                destination_iata TEXT NOT NULL,
                departure_date TEXT NOT NULL,
                response_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS flight_detail_cache (
                cache_key TEXT PRIMARY KEY,
                airline_code TEXT NOT NULL,
                flight_number TEXT NOT NULL,
                departure_date TEXT NOT NULL,
                departure_airport TEXT,
                response_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS airline_code_cache (
                cache_key TEXT PRIMARY KEY,
                airline_name TEXT NOT NULL,
                response_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def _load_cached_payload(self, table_name: str, cache_key: str) -> Tuple[Optional[Any], bool]:
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT response_json, expires_at FROM {table_name} WHERE cache_key = ?",
            (cache_key,),
        )
        row = cursor.fetchone()
        if row is None:
            return (None, False)

        try:
            payload = json.loads(row["response_json"])
        except json.JSONDecodeError:
            return (None, False)

        expires_at = row["expires_at"]
        try:
            is_stale = datetime.fromisoformat(expires_at) < _utc_now()
        except ValueError:
            is_stale = True
        logger.info("cache:read table=%s key=%s stale=%s", table_name, cache_key, is_stale)
        return (payload, is_stale)

    def _store_cached_payload(
        self,
        table_name: str,
        cache_key: str,
        columns: Dict[str, Any],
        payload: Any,
        ttl: timedelta,
    ) -> None:
        now = _utc_now()
        values = dict(columns)
        values["cache_key"] = cache_key
        values["response_json"] = json.dumps(payload)
        values["fetched_at"] = now.isoformat()
        values["expires_at"] = (now + ttl).isoformat()

        column_names = ", ".join(values.keys())
        placeholders = ", ".join(["?"] * len(values))
        update_columns = ", ".join(
            f"{column} = excluded.{column}"
            for column in values.keys()
            if column != "cache_key"
        )
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO {table_name} ({column_names})
            VALUES ({placeholders})
            ON CONFLICT(cache_key) DO UPDATE SET {update_columns}
            """,
            tuple(values.values()),
        )
        self.conn.commit()
        logger.info("cache:write table=%s key=%s expires_at=%s", table_name, cache_key, values["expires_at"])

    def _http_get_json(self, url: str) -> Any:
        logger.info("http:get %s", url.replace(self.api_key, "<api-key>"))
        request = Request(
            url,
            headers={
                "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
                "User-Agent": "MiddleGround/1.0",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=20) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                error_body = ""
            error_message = _extract_error_message(error_body)
            if exc.code == 404 and _is_no_data_message(error_message):
                logger.info(
                    "http:no-data status=%s url=%s message=%s",
                    exc.code,
                    url.replace(self.api_key, "<api-key>"),
                    error_message,
                )
                raise FlightApiNoDataError(error_message or "No details for your input") from exc
            logger.error(
                "http:error status=%s reason=%s url=%s body=%s",
                exc.code,
                exc.reason,
                url.replace(self.api_key, "<api-key>"),
                error_body.strip(),
            )
            raise FlightApiError(
                f"FlightAPI request failed ({exc.code} {exc.reason}). {error_body.strip()}".strip()
            ) from exc
        except URLError as exc:
            logger.error("http:url-error url=%s reason=%s", url.replace(self.api_key, "<api-key>"), exc.reason)
            raise FlightApiError(f"Unable to reach FlightAPI: {exc.reason}") from exc

        try:
            payload = json.loads(raw_body)
            logger.info("http:response url=%s payload=%s", url.replace(self.api_key, "<api-key>"), payload)
            return payload
        except json.JSONDecodeError as exc:
            raise FlightApiError("FlightAPI returned a non-JSON response.") from exc

    def _get_with_cache(
        self,
        *,
        table_name: str,
        cache_key: str,
        url: str,
        ttl: timedelta,
        cache_columns: Dict[str, Any],
        diagnostics_prefix: str,
    ) -> Any:
        cached_payload, is_stale = self._load_cached_payload(table_name, cache_key)
        if cached_payload is not None and not is_stale:
            self.diagnostics[f"{diagnostics_prefix}_cache_hits"] += 1
            logger.info("cache:hit prefix=%s key=%s payload=%s", diagnostics_prefix, cache_key, cached_payload)
            return cached_payload

        try:
            self.diagnostics[f"{diagnostics_prefix}_requests"] += 1
            payload = self._http_get_json(url)
            self._store_cached_payload(table_name, cache_key, cache_columns, payload, ttl)
            logger.info("provider:live-hit prefix=%s key=%s payload=%s", diagnostics_prefix, cache_key, payload)
            return payload
        except FlightApiError:
            if cached_payload is not None:
                self.diagnostics[f"{diagnostics_prefix}_stale_hits"] += 1
                logger.info("cache:stale-hit prefix=%s key=%s payload=%s", diagnostics_prefix, cache_key, cached_payload)
                return cached_payload
            raise

    def resolve_airline_code(self, airline_name: Optional[str]) -> Optional[str]:
        if not airline_name:
            return None

        normalized_name = " ".join(airline_name.split())
        cache_key = f"{AIRLINE_CACHE_KEY_VERSION}:{normalized_name.lower()}"
        encoded_name = urlencode({"name": normalized_name, "type": "airline"})
        url = f"{AIRLINE_CODE_ENDPOINT}/{quote(self.api_key)}?{encoded_name}"

        try:
            payload = self._get_with_cache(
                table_name="airline_code_cache",
                cache_key=cache_key,
                url=url,
                ttl=timedelta(days=AIRLINE_CODE_CACHE_TTL_DAYS),
                cache_columns={"airline_name": normalized_name},
                diagnostics_prefix="airline_code",
            )
        except FlightApiError as exc:
            self.warnings.append(f"Unable to resolve airline code for '{normalized_name}': {exc}")
            return None

        for item in _coerce_sequence(payload):
            if not isinstance(item, dict):
                continue
            airline_code = _pick_str(item, "fs", "iata", "code", "airlineCode")
            if airline_code:
                logger.info("airline-code:resolved name=%s code=%s payload=%s", normalized_name, airline_code.upper(), payload)
                return airline_code.upper()
        logger.info("airline-code:unresolved name=%s payload=%s", normalized_name, payload)
        return None

    def fetch_route_payload(self, origin_iata: str, destination_iata: str, departure_date: str) -> Any:
        logger.info("route:fetch origin=%s destination=%s departure_date=%s", origin_iata, destination_iata, departure_date)
        api_date = _format_api_date(departure_date)
        query = urlencode(
            {
                "date": api_date,
                "airport1": origin_iata,
                "airport2": destination_iata,
            }
        )
        url = f"{TRACK_BY_ROUTE_ENDPOINT}/{quote(self.api_key)}?{query}"
        cache_key = f"{ROUTE_CACHE_KEY_VERSION}:{origin_iata}:{destination_iata}:{departure_date}"
        self.diagnostics["route_pairs_requested"].append(
            {
                "origin": origin_iata,
                "destination": destination_iata,
                "departure_date": departure_date,
            }
        )
        cache_columns = {
            "origin_iata": origin_iata,
            "destination_iata": destination_iata,
            "departure_date": departure_date,
        }
        try:
            return self._get_with_cache(
                table_name="route_cache",
                cache_key=cache_key,
                url=url,
                ttl=timedelta(hours=ROUTE_CACHE_TTL_HOURS),
                cache_columns=cache_columns,
                diagnostics_prefix="route",
            )
        except FlightApiNoDataError:
            self.diagnostics["route_no_data"] += 1
            self._store_cached_payload(
                "route_cache",
                cache_key,
                cache_columns,
                [],
                timedelta(hours=ROUTE_CACHE_TTL_HOURS),
            )
            logger.info(
                "route:no-data origin=%s destination=%s departure_date=%s",
                origin_iata,
                destination_iata,
                departure_date,
            )
            return []

    def fetch_flight_detail(
        self,
        *,
        airline_code: Optional[str],
        flight_number: Optional[str],
        departure_date: str,
        departure_airport: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not airline_code or not flight_number:
            logger.info(
                "detail:skip airline_code=%s flight_number=%s departure_date=%s departure_airport=%s",
                airline_code,
                flight_number,
                departure_date,
                departure_airport,
            )
            return None

        cleaned_airline_code = airline_code.strip().upper()
        cleaned_flight_number = _sanitize_flight_number(flight_number)
        if not cleaned_flight_number:
            logger.info(
                "detail:skip-invalid-number airline_code=%s raw_flight_number=%s departure_date=%s departure_airport=%s",
                cleaned_airline_code,
                flight_number,
                departure_date,
                departure_airport,
            )
            return None

        logger.info(
            "detail:fetch airline_code=%s flight_number=%s departure_date=%s departure_airport=%s",
            cleaned_airline_code,
            cleaned_flight_number,
            departure_date,
            departure_airport,
        )

        self.diagnostics["detail_lookups_attempted"] += 1
        query_values = {
            "num": cleaned_flight_number,
            "name": cleaned_airline_code,
            "date": _format_api_date(departure_date),
        }
        if departure_airport:
            query_values["depap"] = departure_airport.strip().upper()
        query = urlencode(query_values)
        url = f"{FLIGHT_TRACKING_ENDPOINT}/{quote(self.api_key)}?{query}"
        cache_key = (
            f"{DETAIL_CACHE_KEY_VERSION}:{cleaned_airline_code}:{cleaned_flight_number}:{departure_date}:"
            f"{(departure_airport or '').strip().upper()}"
        )

        cache_columns = {
            "airline_code": cleaned_airline_code,
            "flight_number": cleaned_flight_number,
            "departure_date": departure_date,
            "departure_airport": (departure_airport or "").strip().upper() or None,
        }
        try:
            payload = self._get_with_cache(
                table_name="flight_detail_cache",
                cache_key=cache_key,
                url=url,
                ttl=timedelta(hours=DETAIL_CACHE_TTL_HOURS),
                cache_columns=cache_columns,
                diagnostics_prefix="detail",
            )
        except FlightApiNoDataError:
            self.diagnostics["detail_no_data"] += 1
            self._store_cached_payload(
                "flight_detail_cache",
                cache_key,
                cache_columns,
                [],
                timedelta(hours=DETAIL_CACHE_TTL_HOURS),
            )
            logger.info(
                "detail:no-data airline_code=%s flight_number=%s departure_date=%s departure_airport=%s",
                cleaned_airline_code,
                cleaned_flight_number,
                departure_date,
                departure_airport,
            )
            return None
        except FlightApiError as exc:
            self.diagnostics["detail_lookups_failed"] += 1
            self.warnings.append(
                f"Unable to load detail for {cleaned_airline_code}{cleaned_flight_number}: {exc}"
            )
            logger.error(
                "detail:error airline_code=%s flight_number=%s departure_date=%s departure_airport=%s error=%s",
                cleaned_airline_code,
                cleaned_flight_number,
                departure_date,
                departure_airport,
                exc,
            )
            return None

        bundle = _extract_tracking_bundle(payload)
        if bundle:
            self.diagnostics["detail_lookups_succeeded"] += 1
            logger.info(
                "detail:bundle airline_code=%s flight_number=%s departure_date=%s departure_airport=%s payload=%s",
                cleaned_airline_code,
                cleaned_flight_number,
                departure_date,
                departure_airport,
                bundle,
            )
            return bundle

        self.diagnostics["detail_lookups_failed"] += 1
        logger.info(
            "detail:empty-bundle airline_code=%s flight_number=%s departure_date=%s departure_airport=%s payload=%s",
            cleaned_airline_code,
            cleaned_flight_number,
            departure_date,
            departure_airport,
            payload,
        )
        return None

    def _build_endpoint(
        self,
        endpoint_name: str,
        *,
        detail_data: Optional[Dict[str, Any]],
        fallback_airport_iata: str,
        fallback_airport_name: Optional[str],
        fallback_time_raw: Optional[str],
        base_date: str,
    ) -> FlightEndpoint:
        detail_data = detail_data or {}
        base_iso = _parse_route_datetime(fallback_time_raw, base_date)
        precise_time = _parse_detail_datetime(
            detail_data,
            "departureDateTime" if endpoint_name == "departure" else "arrivalDateTime",
            "scheduledDateTime",
            "estimatedDateTime",
            "actualDateTime",
        )
        scheduled_time = precise_time or base_iso
        estimated_time = _parse_detail_datetime(detail_data, "estimatedDateTime") or precise_time
        actual_time = _parse_detail_datetime(
            detail_data,
            "actualDateTime",
            "departureDateTime" if endpoint_name == "departure" else "arrivalDateTime",
        )

        airport_name = _coalesce(
            _pick_str(detail_data, "airport"),
            fallback_airport_name,
        )
        airport_code = _coalesce(
            _pick_str(detail_data, "airportCode", "iata", "fs"),
            fallback_airport_iata,
        )
        return FlightEndpoint(
            airport=airport_name,
            iata=(airport_code or fallback_airport_iata).upper(),
            terminal=_pick_str(detail_data, "terminal"),
            gate=_pick_str(detail_data, "gate"),
            baggage=_pick_str(detail_data, "baggage"),
            scheduled=scheduled_time,
            estimated=estimated_time,
            actual=actual_time,
        )

    def _normalize_route_item(
        self,
        item: Dict[str, Any],
        *,
        origin_iata: str,
        destination_iata: str,
        departure_date: str,
    ) -> Optional[Flight]:
        airline_name = _coalesce(
            _pick_str(item, "Airline", "airline", "carrier"),
            _pick_nested_str(item, ("airline", "name")),
        )
        flight_number = _sanitize_flight_number(
            _coalesce(
                _pick_str(item, "FlightNumber", "flightNumber", "number"),
                _pick_nested_str(item, ("flight", "number")),
            )
        )
        status = _coalesce(
            _pick_str(item, "displayStatus", "DisplayStatus"),
            _pick_str(item, "Status", "status"),
            _pick_nested_str(item, ("status", "text")),
        )
        operated_by = _pick_str(item, "Operated By", "operatedBy")
        operated_airline_name, operated_flight_number = _split_operated_by(operated_by)

        route_departure_time = _pick_str(item, "DepartureTime", "departureTime")
        route_arrival_time = _pick_str(item, "ArrivalTime", "arrivalTime")

        marketing_airline_code = _coalesce(
            _pick_str(item, "AirlineCode", "airlineCode", "airline_iata", "airlineIata", "fs"),
            _pick_nested_str(item, ("airline", "iata")),
            _pick_nested_str(item, ("airline", "fs")),
            _pick_nested_str(item, ("airline", "code", "iata")),
        )
        lookup_airline_name = operated_airline_name or airline_name
        lookup_flight_number = operated_flight_number or flight_number
        airline_code = marketing_airline_code

        if not airline_code and lookup_airline_name:
            airline_code = self.resolve_airline_code(lookup_airline_name)

        detail_bundle = self.fetch_flight_detail(
            airline_code=airline_code,
            flight_number=lookup_flight_number,
            departure_date=departure_date,
            departure_airport=origin_iata,
        )

        departure_detail = _pick_dict(detail_bundle, "departure") if detail_bundle else None
        arrival_detail = _pick_dict(detail_bundle, "arrival") if detail_bundle else None
        airline_detail = _pick_dict(detail_bundle, "airline") if detail_bundle else None
        flight_detail = _pick_dict(detail_bundle, "flight") if detail_bundle else None

        airline_name = _coalesce(
            _pick_str(airline_detail, "name"),
            lookup_airline_name,
            airline_name,
        )
        airline_code = _coalesce(
            _pick_str(airline_detail, "iata", "fs"),
            _pick_nested_str(airline_detail, ("code", "iata")),
            airline_code,
        )
        flight_number = _sanitize_flight_number(
            _coalesce(
                _pick_str(flight_detail, "number"),
                lookup_flight_number,
                flight_number,
            )
        )
        flight_code = _coalesce(
            _pick_str(flight_detail, "iata"),
            f"{airline_code}{flight_number}" if airline_code and flight_number else None,
        )

        if not flight_code and not flight_number and not route_departure_time and not route_arrival_time:
            return None

        departure_endpoint = self._build_endpoint(
            "departure",
            detail_data=departure_detail,
            fallback_airport_iata=origin_iata,
            fallback_airport_name=origin_iata,
            fallback_time_raw=route_departure_time,
            base_date=departure_date,
        )
        arrival_endpoint = self._build_endpoint(
            "arrival",
            detail_data=arrival_detail,
            fallback_airport_iata=destination_iata,
            fallback_airport_name=destination_iata,
            fallback_time_raw=route_arrival_time,
            base_date=departure_date,
        )

        raw_result = FlightResult(
            flight_date=departure_date,
            flight_status=status,
            departure=departure_endpoint,
            arrival=arrival_endpoint,
            airline=AirlineInfo(
                name=airline_name,
                iata=(airline_code or "").upper() or None,
            ),
            flight=FlightInfo(
                number=flight_number,
                iata=flight_code,
                icao=_pick_str(flight_detail, "icao"),
            ),
        )
        return Flight(
            raw_result=raw_result,
            departure_iata=departure_endpoint.iata,
            arrival_iata=arrival_endpoint.iata,
            flight_date=departure_date,
            flight_status=status,
            flight_iata=flight_code,
            airline_iata=(airline_code or "").upper() or None,
        )

    def load_route_flights(
        self,
        origin_iata: str,
        destination_iata: str,
        departure_date: str,
    ) -> List[Flight]:
        route_payload = self.fetch_route_payload(origin_iata, destination_iata, departure_date)
        logger.info(
            "route:payload origin=%s destination=%s departure_date=%s payload=%s",
            origin_iata,
            destination_iata,
            departure_date,
            route_payload,
        )
        flights: List[Flight] = []
        for item in _extract_route_flights(route_payload):
            if not isinstance(item, dict):
                continue
            normalized = self._normalize_route_item(
                item,
                origin_iata=origin_iata,
                destination_iata=destination_iata,
                departure_date=departure_date,
            )
            if normalized is not None:
                flights.append(normalized)
        logger.info(
            "route:normalized origin=%s destination=%s departure_date=%s flights=%s",
            origin_iata,
            destination_iata,
            departure_date,
            flights,
        )
        return flights


def load_flightapi_route_flights(
    *,
    api_key: str,
    origin_airports: Optional[Iterable[str]],
    destination_airports: Optional[Iterable[str]],
    departure_date: Optional[str],
) -> FlightApiFetchResult:
    normalized_origins = _normalize_iata_codes(origin_airports)
    normalized_destinations = _normalize_iata_codes(destination_airports)

    if not normalized_origins or not normalized_destinations:
        return FlightApiFetchResult(
            flights=[],
            diagnostics={
                "provider": "flightapi",
                "route_requests": 0,
                "route_cache_hits": 0,
                "route_stale_hits": 0,
                "route_no_data": 0,
                "detail_requests": 0,
                "detail_cache_hits": 0,
                "detail_stale_hits": 0,
                "detail_no_data": 0,
                "airline_code_requests": 0,
                "airline_code_cache_hits": 0,
                "airline_code_stale_hits": 0,
                "route_pairs_requested": [],
                "detail_lookups_attempted": 0,
                "detail_lookups_succeeded": 0,
                "detail_lookups_failed": 0,
            },
        )

    if not departure_date:
        raise FlightApiInputError(
            "Departure date is required to search live flights between origin and destination airports."
        )

    flights: List[Flight] = []
    with FlightApiClient(api_key=api_key) as client:
        for destination_iata in normalized_destinations:
            for origin_iata in normalized_origins:
                if origin_iata == destination_iata:
                    continue
                flights.extend(
                    client.load_route_flights(
                        origin_iata=origin_iata,
                        destination_iata=destination_iata,
                        departure_date=departure_date,
                    )
                )

        diagnostics = dict(client.diagnostics)
        diagnostics["origin_airports"] = normalized_origins
        diagnostics["destination_airports"] = normalized_destinations
        diagnostics["fetched_flights"] = len(flights)
        return FlightApiFetchResult(
            flights=flights,
            diagnostics=diagnostics,
            warnings=list(client.warnings),
        )
