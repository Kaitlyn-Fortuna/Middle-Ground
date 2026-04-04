# MiddleGround

MiddleGround helps a group starting from different origin airports find a good shared destination.

It combines:
- airport preference ranking from local airport data
- live route lookup from FlightAPI
- per-origin flight scoring
- a destination-level combined ranking shown in the browser

## Current Status

The app is now wired to live FlightAPI endpoints for flight route/tracking data.

Important caveats:
- The FlightAPI key is entered in the website UI and sent to the backend in the `X-API-Key` header.
- The backend does not use a FlightAPI key from `.env`.
- Flight timing/status data is live from FlightAPI.
- Ticket price is still estimated locally because the connected tracking endpoints do not return fares.
- FlightAPI responses are cached in SQLite to reduce repeated credit usage.

## What The App Does

1. The user selects:
   - origin airports
   - departure date
   - return date
   - optional airport preference filters
   - optional flight filters
2. The backend ranks destination airports.
3. For each destination candidate, the backend looks for flights from every selected origin airport.
4. A destination is only kept if every selected origin has a flight to that destination.
5. The app scores:
   - the airport
   - each flight
   - the destination overall
6. The UI shows the ranked destinations with expandable airport and flight breakdowns.

## Current Ranking Behavior

### Airport-side filters

Supported airport preference categories:
- `weather_preferences`
  - `hot`, `warm`, `mild`, `cool`, `cold`
- `conditions_preferences`
  - `sunny`, `dry`, `wet`, `low humidity`, `high humidity`
- `geography_preferences`
  - `coastal`, `beach`, `urban`, `mountainous`

These are scored from data in [`data/airport_data.db`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/data/airport_data.db).

### Flight-side filters

Currently supported:
- `max_flight_time`
- `max_flight_cost`
- `departure_date`

Notes:
- `max_flight_cost` currently uses an estimated ticket price, not live fare data.
- `return_date` is currently required for the trip flow, but outbound route lookup is the live part that is fully wired today.

### No airport filters fallback

If the user does not choose any `weather`, `conditions`, or `geography` filters:
- destination candidates are ordered by airport population popularity from the airport database
- combined ranking is then driven by flight-side scoring

This prevents the app from falling back to arbitrary-looking airport order when the user only cares about travel constraints.

### Destination candidate count

The combined search currently scans up to the top `10` destination candidates.

If fewer than 10 destinations have flights from all selected origin airports, the app returns as many as it can.

## Required Inputs For Optimize Travel

The UI and backend both require all of the following before combined ranking will run:
- at least one origin airport
- a departure date
- a return date
- a submitted API key

If any are missing, the app returns an error instead of running a partial search.

## Project Structure

- [`main.html`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/main.html): frontend layout
- [`main.js`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/main.js): frontend state, storage, API calls, rendering
- [`main.css`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/main.css): frontend styling
- [`backend/app.py`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/backend/app.py): Flask API
- [`backend/airportFiltering.py`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/backend/airportFiltering.py): airport ranking logic
- [`backend/flightFiltering.py`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/backend/flightFiltering.py): combined destination + flight ranking logic
- [`backend/flightApiProvider.py`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/backend/flightApiProvider.py): FlightAPI integration and SQLite caching
- [`backend/parseFilters.py`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/backend/parseFilters.py): request/filter parsing
- [`backend/parseResults.py`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/backend/parseResults.py): normalized flight result parsing
- [`data/airport_data.db`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/data/airport_data.db): airport dataset
- [`data/flight_api_cache.db`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/data/flight_api_cache.db): cached FlightAPI responses

## Local Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install backend dependencies

```bash
python -m pip install -r backend/requirements.txt
```

### 3. Run the backend

```bash
python backend/app.py
```

Backend runs at:
- `http://127.0.0.1:5001`

### 4. Run the frontend

Serve [`main.html`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/main.html) with any static server, such as VS Code Live Server.

Typical frontend URLs:
- `http://127.0.0.1:5500/main.html`
- `http://localhost:5500/main.html`

## CORS / Ports

- Frontend: `localhost` or `127.0.0.1` on a local dev port
- Backend: `127.0.0.1:5001`

[`backend/app.py`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/backend/app.py) allows CORS for localhost and `127.0.0.1`.

## API Key Behavior

- The user enters the FlightAPI key in the website UI.
- The key is stored in browser storage so it survives refresh.
- Requests to `POST /api/rank-combined` include the key in the `X-API-Key` header.
- If no key has been submitted, the UI and backend both return an error.

## Browser Storage

The frontend stores:
- submitted API key state
- selected trip info
- selected filters
- combined results

That allows the page state to survive refreshes.

The UI also includes separate reset actions for:
- API key
- trip/filter/results state

## FlightAPI Integration

The app currently uses these FlightAPI docs/endpoints:
- Track Flights between Airports
- Flight Tracking API
- Airline & Airport Code API as a fallback helper when airline code lookup is needed

Current usage:
- route search comes from the route-tracking endpoint
- flight detail enrichment comes from the flight-tracking endpoint
- airline-code lookup is used only when needed for detail requests

## Caching

FlightAPI responses are cached in [`data/flight_api_cache.db`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/data/flight_api_cache.db).

Cached tables include:
- route lookups
- per-flight detail lookups
- airline code lookups

The goal is to reduce repeated FlightAPI credit usage for the same searches.

## API Endpoints

### `GET /api/health`

Health check.

Example response:

```json
{
  "status": "ok",
  "message": "Flask server is running"
}
```

### `GET /api/airports`

Returns the supported domestic large airports used in the UI airport picker.

### `POST /api/rank`

Airport-only ranking endpoint.

Query params:
- `limit` optional integer

Body:
- filter payload JSON

### `POST /api/rank-combined`

Main Optimize Travel endpoint.

Query params:
- `limit` optional integer, default `25`

Header:

```http
X-API-Key: <user-entered-flightapi-key>
```

Example request body:

```json
{
  "departure_date": "2026-04-08",
  "return_date": "2026-04-16",
  "airports": ["LAX", "DTW", "LGA"],
  "weather_preferences": ["warm"],
  "conditions_preferences": ["sunny"],
  "geography_preferences": ["coastal"],
  "max_flight_time": 6,
  "max_flight_cost": 500
}
```

Response includes:
- ranked destination airports
- airport score and flight score
- combined score
- combined estimated trip price
- per-origin flight rows
- airport breakdown
- flight breakdown
- diagnostics

## Important Diagnostics

`/api/rank-combined` diagnostics now include fields like:
- `flight_data_source`
- `flight_price_source`
- `flight_price_note`
- `airport_ranking_mode`
- `candidate_destination_limit`
- `selected_origin_airports`
- `excluded_destinations_missing_origins`
- provider cache/request diagnostics

These are especially useful when debugging live API behavior.

## Notes About Prices

The current connected FlightAPI endpoints do not return live ticket fares.

So:
- `max_flight_cost` is supported in the app
- `All-in` is shown in the UI
- but both are based on the local estimator in [`backend/flightFiltering.py`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/backend/flightFiltering.py#L132)

If real price filtering is needed, a fare/pricing API will need to be added separately.

## Legacy / Local Test Data

[`data/results-test.json`](/Users/kyle/Library/CloudStorage/OneDrive-UniversityofToledo/Spring%202026/EECS3550/MiddleGround/data/results-test.json) is still in the repo for earlier local testing, but the live combined flow is no longer driven by that file.

## Recommended Test Flow

1. Start backend.
2. Serve the frontend locally.
3. Enter a valid FlightAPI key in the UI.
4. Select:
   - at least one origin airport
   - departure date
   - return date
5. Add optional airport and flight filters.
6. Click `Optimize Travel`.

## Known Limitations

- Return-date-aware live flight matching is not fully implemented yet.
- Fare data is estimated, not live.
- A cached route can still satisfy a later repeated search without re-contacting FlightAPI.
- Invalid-key behavior can look less strict when a matching route is already cached.
