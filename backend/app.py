from pathlib import Path
import sqlite3

from flask import Flask, jsonify, request
from flask_cors import CORS

from parseFilters import (
    parse_filters_api_json
)
from airportFiltering import (
    format_rank_results,
    import_airport_data,
    initialize_ranked_airports,
    overall_rank,
    run_all_ranks,
)


app = Flask(__name__)
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR.parent / "data"

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


@app.post("/api/rank")
def rank_airports():
    payload = request.get_json(silent=True)
    filters = parse_filters_api_json(payload)

    limit_raw = request.args.get("limit")
    limit = None
    if limit_raw is not None:
        try:
            limit = max(1, int(limit_raw))
        except ValueError:
            return jsonify({"status": "error", "message": "Query param 'limit' must be an integer"}), 400

    try:
        airports = import_airport_data()
        ranked_airports = initialize_ranked_airports(airports)
        final_rank = overall_rank(run_all_ranks(ranked_airports, filters), filters)
        results = format_rank_results(final_rank, limit=limit)

        return jsonify(
            {
                "status": "ok",
                "count": len(results),
                "results": results,
            }
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.post("/api/rank-combined")
def rank_combined():
    payload = request.get_json(silent=True)
    filters = parse_filters_api_json(payload)

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
        airport_rank = overall_rank(run_all_ranks(ranked_airports, filters), filters)
        limited_ranked = airport_rank.ranked[:limit]
        limited_results = []

        for idx, ranked_airport in enumerate(limited_ranked, start=1):
            limited_results.append(
                {
                    "rank": idx,
                    "iata_code": ranked_airport.airport.iata_code,
                    "airport_name": ranked_airport.airport.name,
                    "percent_match": round(ranked_airport.percent_match, 3)
                    if ranked_airport.percent_match is not None
                    else None,
                    "scores": ranked_airport.scores,
                }
            )

        return jsonify(
            {
                "status": "ok",
                "count": len(limited_results),
                "results": limited_results,
                "active_score_keys": {
                    "airport": sorted(airport_rank.active_score_keys),
                    "flight": [],
                },
                "message": "Flight ranking is currently disabled. Trip data is reserved for future flight ranking and does not affect airport ranking.",
            }
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
