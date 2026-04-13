from pathlib import Path
import logging
import sqlite3

from flask import Flask, jsonify, request
from flask_cors import CORS

from parseFilters import (
    parse_filters_api_json
)
from airportFiltering import (
    import_airport_data,
    initialize_ranked_airports,
    overall_rank,
    run_all_ranks,
)
from flightFiltering import (
    MAX_DESTINATION_CANDIDATES,
    build_combined_destination_rankings,
)
from flightApiProvider import FlightApiError, FlightApiInputError


app = Flask(__name__)
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR.parent / "data"

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

logger = logging.getLogger("middleground.backend")

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                r"^https?://localhost(:\d+)?$",
                r"^https?://127\.0\.0\.1(:\d+)?$",
            ]
        }
    },
)


def load_domestic_large_airports():
    db_path = DATA_DIR / "airport_data.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                UPPER(TRIM(iata_code)) AS iata_code,
                name,
                municipality,
                iso_region
            FROM airport_data
            WHERE iso_country = 'US'
              AND type = 'large_airport'
              AND iata_code IS NOT NULL
              AND TRIM(iata_code) <> ''
            ORDER BY name COLLATE NOCASE
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "iata_code": row["iata_code"],
                "name": row["name"],
                "municipality": row["municipality"],
                "iso_region": row["iso_region"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def _mask_api_key(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return "<missing>"
    if len(cleaned) <= 6:
        return f"{cleaned[:1]}***{cleaned[-1:]}"
    return f"{cleaned[:3]}***{cleaned[-3:]}"


@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok", "message": "Flask server is running"})


@app.get("/api/airports")
def list_airports():
    try:
        airports = load_domestic_large_airports()
        return jsonify(
            {
                "status": "ok",
                "count": len(airports),
                "results": airports,
            }
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.post("/api/rank-combined")
def rank_combined():
    api_key = (request.headers.get("X-API-Key") or "").strip()
    if not api_key:
        return jsonify({"status": "error", "message": "Missing API key. Submit your API key from the website first."}), 400

    payload = request.get_json(silent=True)
    filters = parse_filters_api_json(payload)
    logger.info(
        "rank-combined:start api_key=%s origins=%s departure_date=%s return_date=%s weather=%s conditions=%s geography=%s max_flight_time=%s max_flight_cost=%s",
        _mask_api_key(api_key),
        len(filters.airports or []),
        filters.departure_date,
        filters.return_date,
        filters.weather_preferences,
        filters.conditions_preferences,
        filters.geography_preferences,
        filters.max_flight_time,
        filters.max_flight_cost,
    )

    limit_raw = request.args.get("limit")
    limit = 25
    if limit_raw is not None:
        try:
            limit = max(1, int(limit_raw))
        except ValueError:
            return jsonify({"status": "error", "message": "Query param 'limit' must be an integer"}), 400

    try:
        airports = import_airport_data()
        ranked_airports = initialize_ranked_airports(airports)
        logger.info("rank-combined:airport-ranking-start airport_count=%s", len(ranked_airports))
        airport_rank = overall_rank(run_all_ranks(ranked_airports, filters), filters)
        logger.info(
            "rank-combined:airport-ranking-complete active_score_keys=%s top10=%s",
            sorted(airport_rank.active_score_keys),
            [
                {
                    "iata_code": ranked.airport.iata_code,
                    "percent_match": ranked.percent_match,
                }
                for ranked in airport_rank.ranked[:10]
            ],
        )
        combined = build_combined_destination_rankings(
            airport_ranked=airport_rank.ranked,
            filters=filters,
            api_key=api_key,
            destination_candidate_limit=MAX_DESTINATION_CANDIDATES,
        )
        limited_results = combined["results"][:limit]
        logger.info(
            "rank-combined:done results=%s message=%s diagnostics=%s",
            len(limited_results),
            combined["message"],
            combined["diagnostics"],
        )

        return jsonify(
            {
                "status": "ok",
                "count": len(limited_results),
                "results": limited_results,
                "active_score_keys": {
                    "airport": sorted(airport_rank.active_score_keys),
                    "flight": combined["active_flight_score_keys"],
                },
                "diagnostics": combined["diagnostics"],
                "message": combined["message"],
            }
        )
    except FlightApiInputError as exc:
        logger.warning("rank-combined:input-error %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 400
    except FlightApiError as exc:
        logger.error("rank-combined:provider-error %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 502
    except Exception as exc:
        logger.exception("rank-combined:unexpected-error")
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
