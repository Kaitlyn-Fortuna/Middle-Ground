# MiddleGround

MiddleGround helps groups traveling from different origin airports find the best shared destination. The current frontend is a Vue 3 + Vite app in `src/`, and the backend is a Flask API in `backend/`.

## What it does

1. Loads origin airport options from the backend.
2. Accepts group origin airports, trip dates, and preference filters in the Vue UI.
3. Ranks destination airports using local airport/weather/geography data.
4. Fetches route data from FlightAPI for each selected origin airport.
5. Keeps only destinations that every selected origin can reach.
6. Scores the best route per origin by time, estimated cost, and departure-date alignment.
7. Returns combined destination results with airport breakdowns and per-origin flight summaries.

## Architecture

- Frontend: `src/` (`Vue 3`, `Vite`, `TypeScript`)
- Backend API: `backend/app.py`
- Airport ranking: `backend/airportFiltering.py`
- Flight API + cache: `backend/flightApiProvider.py`
- Combined ranking: `backend/flightFiltering.py`
- Request parsing: `backend/parseFilters.py`
- Shared models: `backend/models.py`
- Data stores:
  - `data/airport_data.db`
  - `data/flight_api_cache.db`

## Environment

Create a root `.env` file:

```env
FLIGHTAPI_API_KEY=replace-with-your-flightapi-key
VITE_API_BASE_URL=http://127.0.0.1:5001/api
```

Notes:

- `FLIGHTAPI_API_KEY` is read by the Flask backend when the frontend does not send an `X-API-Key` header.
- The Vue frontend no longer has an API-key field in the UI.
- `VITE_API_BASE_URL` tells the Vue app where the Flask API is running.
- The local `.env` file is gitignored.

## API behavior

### `GET /api/health`

Simple health check.

### `GET /api/airports`

Returns the domestic large-airport list used by the Vue airport picker.

### `POST /api/rank-combined`

Primary optimize endpoint used by the Vue UI.

Inputs:

- Query param: `limit`
- JSON body:
  - `departure_date`
  - `return_date`
  - `airports`
  - optional airport preference filters
  - `max_flight_time`
  - `max_flight_cost`
- API key:
  - preferred source: `FLIGHTAPI_API_KEY` in `.env`
  - optional override: `X-API-Key` request header

Sample request payload:

```json
{
  "departure_date": "2026-04-20",
  "return_date": "2026-04-27",
  "airports": ["DTW", "LGA", "ATL"],
  "weather_preferences": ["warm", "mild"],
  "conditions_preferences": ["sunny", "dry"],
  "geography_preferences": ["coastal", "urban"],
  "max_flight_time": 6,
  "max_flight_cost": 450
}
```

Sample files:

- Request body example: `data/filters-sample.json`
- Response example: `data/rank-combined-response-sample.json`

## Caching

FlightAPI responses are cached in SQLite (`data/flight_api_cache.db`) for route, flight-detail, and airline-code lookups.

Notes:

- Route data is always live-or-cache.
- Flight detail enrichment is optional and disabled by default to avoid noisy `/airline` failures.
- `ENABLE_FLIGHT_DETAIL_ENRICHMENT=1` enables detail enrichment.

## Diagnostics

`/api/rank-combined` includes diagnostics to help debug live behavior, including:

- `candidate_destination_limit`
- `initial_top_ranked_airport_candidates`
- `candidate_destinations_considered`
- `excluded_destinations_missing_origins`
- `route_errors`
- `provider`

## Local development

1. Install backend dependencies:

```bash
python3 -m pip install -r backend/requirements.txt
```

2. Start the backend:

```bash
python3 backend/app.py
```

3. Install frontend dependencies:

```bash
npm install
```

4. Start the Vue frontend:

```bash
npm run dev
```

Default local URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://127.0.0.1:5001`

## Vue frontend flow

The Vue app does two backend calls:

1. `GET /api/airports` to populate each group member's airport picker.
2. `POST /api/rank-combined?limit=10` to fetch ranked shared destinations.

The returned result cards display:

- destination rank and combined score
- airport score and airport breakdown
- estimated total group flight price
- best flight per selected origin airport
