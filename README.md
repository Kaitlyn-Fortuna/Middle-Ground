# middle-ground

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Type-Check, Compile and Minify for Production

```sh
npm run build
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```

# MiddleGround

MiddleGround helps groups traveling from different origin airports find the best shared destination.

## What it does

1. Ranks destination airports using local airport/weather/geography data.
2. Starts with the top 10 ranked destination candidates and requests real route data from FlightAPI for each selected origin airport.
3. If fewer than 5 valid shared destinations are found, continues scanning further down the ranked list until it finds at least 5 or reaches the end.
4. Keeps only destinations where every selected origin has at least one route.
5. Scores the best route per origin by time/cost/date alignment.
6. Combines airport score + flight score into one ranked destination list.
7. Renders ranked cards in the UI with airport and flight breakdowns.

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

## Destination search strategy

- Candidate scan starts with the top 10 ranked airports.
- The backend continues past top 10 if needed to find at least 5 shared destinations.
- If fewer than 5 exist in total, it returns whatever it found.
- If none exist, response message is:
  - `There isn't an airport that has all selected origin airports in common.`

## UI behavior updates

- Empty state now says: “Choose filters and click Optimize Travel to load results.”
- If optimize returns no shared destinations, UI shows the same explicit “no common airport” message.
- If the API returns an error status, UI shows `Error: ... Please retry.`
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
