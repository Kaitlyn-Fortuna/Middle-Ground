# MiddleGround

MiddleGround helps groups traveling from different origin airports find the best shared destination.

## What it does

1. Ranks destination airports using local airport/weather/geography data.
2. For the top 10 ranked destination candidates, requests real route data from FlightAPI for each selected origin airport.
3. Keeps only destinations where every selected origin has at least one route.
4. Scores the best route per origin by time/cost/date alignment.
5. Combines airport score + flight score into one ranked destination list.
6. Renders ranked cards in the UI with airport and flight breakdowns.

## Current architecture

- Frontend: `main.html`, `main.js`, `main.css`
- Backend API: `backend/app.py`
- Airport ranking: `backend/airportFiltering.py`
- Flight API + cache: `backend/flightApiProvider.py`
- Combined ranking: `backend/flightFiltering.py`
- Request parsing: `backend/parseFilters.py`
- Shared models: `backend/models.py`
- Data stores:
  - `data/airport_data.db`
  - `data/flight_api_cache.db`

All app models are centralized in `backend/models.py`.

## API behavior

### `GET /api/health`
Simple health check.

### `GET /api/airports`
Returns domestic large airports for the picker UI.

### `POST /api/rank`
Airport-only ranking endpoint.

### `POST /api/rank-combined`
Primary optimize endpoint used by the UI.

Required request header:

```http
X-API-Key: <your-flightapi-key>
```

Expected body fields:
- `departure_date`
- `return_date`
- `airports` (origins)
- optional airport preference filters
- `max_flight_time`
- `max_flight_cost`

## Caching

FlightAPI responses are cached in SQLite (`data/flight_api_cache.db`) for route/detail/code lookups.

Notes:
- Route data is always live-or-cache.
- Flight detail enrichment is optional and disabled by default to avoid noisy `/airline` failures:
  - `ENABLE_FLIGHT_DETAIL_ENRICHMENT=1` to enable
  - default is off

## Diagnostics

`/api/rank-combined` includes diagnostics to help debug live behavior:
- `candidate_destination_limit`
- `initial_top_ranked_airport_candidates`
- `candidate_destinations_considered`
- `excluded_destinations_missing_origins`
- `route_errors` (route call failures by origin/destination)
- `provider` (cache/request counters and enrichment mode)

## UI behavior updates

- Empty state now says: “Choose filters and click Optimize Travel to load results.”
- If route lookup fails, UI shows an explicit error/retry-style message instead of generic guidance.
- Flight durations are displayed in readable text (`1 hour 30 minutes`).

## Local run

1. Install backend deps:

```bash
python -m pip install -r backend/requirements.txt
```

2. Start backend:

```bash
python backend/app.py
```

3. Serve frontend (`main.html`) with a local static server (Live Server is fine).

Backend URL: `http://127.0.0.1:5001`

