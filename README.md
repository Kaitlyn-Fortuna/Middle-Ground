# MiddleGround

MiddleGround is a destination ranking prototype with:

- Frontend (`main.html`, `main.js`, `main.css`) for selecting filters and viewing ranked routes
- Flask backend API (`backend/app.py`) for airport ranking and combined airport+flight ranking
- SQLite airport dataset (`data/airport_data.db`)
- Synthetic flight dataset for testing (`data/results-text.json`)

## Architecture Overview

The app currently uses a two-stage ranking flow:

1. Rank airports with **weather / conditions / geography** preferences.
2. Rank flights with **flight-time preference**.
3. Combine scores into a final route score:

`total_score = (airport_score + flight_score) / 2`

This allows airport-level preferences and flight-level logistics to contribute equally.

## Ports and CORS

- Frontend: `http://localhost:5500` (or `127.0.0.1:5500`)
- Backend: `http://127.0.0.1:5001`

`backend/app.py` enables CORS for localhost/127.0.0.1 on any port.

## Setup

### 1) Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
python -m pip install -r backend/requirements.txt
```

### 3) Run backend

```bash
python backend/app.py
```

### 4) Run frontend

Serve `main.html` with any static server (for example VS Code Live Server) on port `5500`:

- `http://127.0.0.1:5500/main.html`
- `http://localhost:5500/main.html`

## Ranking Inputs (Filter Payload)

Supported filter fields (see `backend/parseFilters.py`):

- `weather_preferences: string[]`
  - `hot`, `warm`, `mild`, `cool`, `cold`
- `conditions_preferences: string[]`
  - `sunny`, `dry`, `wet`, `low humidity`, `high humidity`
- `geography_preferences: string[]`
  - `coastal`, `beach`, `urban`, `mountainous`
- `max_flight_time: number` (hours)
- Also parsed but not fully implemented yet: `max_connections`, `budget_cap`, `prefer_nonstop`, `domestic_only`

Empty arrays are normalized to `None`, so unselected categories do not add zero-score penalties.

## Scoring Model

### Airport score (0.0 to 1.0)

Airport scoring is computed from selected airport-side dimensions only:

- temperature bands
- sun
- precipitation (`dry` / `wet`)
- humidity (`low humidity` / `high humidity`)
- geography (`coastal`, `beach`, `urban`, `mountainous`)

For each airport, `percent_match` is the average of its active airport scores.

### Flight score (0.0 to 1.0)

Current flight ranking uses `max_flight_time`:

- `1.0` when `duration_hours <= max_flight_time`
- otherwise logistic decay toward `0.0`

### Combined score (0.0 to 1.0)

For each ranked flight:

- `airport_score = destination airport percent_match`
- `flight_score = flight percent_match`
- `total_score = (airport_score + flight_score) / 2`

Results are sorted by `total_score` descending.

## API Endpoints

### `GET /api/health`

Health check endpoint.

Example response:

```json
{
  "status": "ok",
  "message": "Flask server is running"
}
```

### `POST /api/rank`

Airport-only ranking endpoint.

Query params:

- `limit` (optional, integer)

Body: filter payload JSON.

Example response:

```json
{
  "status": "ok",
  "count": 25,
  "results": [
    {
      "rank": 1,
      "iata_code": "ABQ",
      "percent_match": 0.91
    }
  ]
}
```

### `POST /api/rank-combined`

Combined airport + flight ranking endpoint (used by current UI).

Query params:

- `limit` (optional, integer; default `25`)

Body example:

```json
{
  "weather_preferences": ["warm"],
  "conditions_preferences": ["sunny", "low humidity"],
  "geography_preferences": ["coastal"],
  "max_flight_time": 6
}
```

Response highlights:

- route fields (`departure_iata`, `arrival_iata`, `flight_iata`, `airline_iata`)
- score breakdown (`percent_match_airport`, `percent_match_flight`, `percent_match_total`)
- details used by filters (`flight_time_hours`, schedule times, per-dimension score maps)

Example (trimmed):

```json
{
  "status": "ok",
  "count": 3,
  "results": [
    {
      "rank": 1,
      "departure_iata": "PIT",
      "arrival_iata": "SMF",
      "flight_iata": "F94278",
      "flight_time_hours": 3.5,
      "percent_match_airport": 0.831,
      "percent_match_flight": 1.0,
      "percent_match_total": 0.916
    }
  ],
  "active_score_keys": {
    "airport": ["coastal", "low humidity", "sunny", "temperature"],
    "flight": ["flight_time"]
  }
}
```

## Data Files

- `data/airport_data.db`: airport features used for airport ranking.
- `data/results-text.json`: synthetic domestic flight dataset for combined ranking tests.
- `data/results-test.json`: smaller fallback dataset.

`/api/rank-combined` attempts to load `results-text.json`, then falls back to `results-test.json` if needed.

## Frontend Notes

- The UI includes a max-flight-time slider tied to `max_flight_time`.
- Request and raw API-response JSON panels are fixed-height with internal scrolling.
- Ranked route cards show:
  - departure and arrival airports
  - airline / flight code / status
  - flight time
  - airport, flight, and total percent-match breakdown
