from pathlib import Path

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
from parseResults import (
    load_flights_dataset_json
)
from flightFiltering import (
    build_destination_rank_map,
    compute_flight_duration_hours,
    initialize_ranked_flights,
    overall_flight_rank,
    run_all_flight_ranks,
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


@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok", "message": "Flask server is running"})


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
        destination_rank_map = build_destination_rank_map(airport_rank.ranked)

        results_text_path = DATA_DIR / "results-text.json"
        if not results_text_path.exists():
            results_text_path = DATA_DIR / "results-test.json"

        flights = load_flights_dataset_json(results_text_path)
        ranked_flights = initialize_ranked_flights(flights, destination_rank_map)
        flight_rank = overall_flight_rank(run_all_flight_ranks(ranked_flights, filters), filters)

        combined_results = []
        for ranked_flight in flight_rank.ranked:
            airport_percent = (
                ranked_flight.destination_airport_rank.percent_match
                if ranked_flight.destination_airport_rank is not None and ranked_flight.destination_airport_rank.percent_match is not None
                else 0.0
            )
            flight_percent = ranked_flight.percent_match if ranked_flight.percent_match is not None else 0.0
            total_percent = (airport_percent + flight_percent) / 2.0
            flight_time_hours = compute_flight_duration_hours(ranked_flight.flight)

            combined_results.append(
                {
                    "departure_iata": ranked_flight.flight.departure_iata,
                    "arrival_iata": ranked_flight.flight.arrival_iata,
                    "flight_iata": ranked_flight.flight.flight_iata,
                    "airline_iata": ranked_flight.flight.airline_iata,
                    "flight_status": ranked_flight.flight.flight_status,
                    "flight_date": ranked_flight.flight.flight_date,
                    "flight_time_hours": round(flight_time_hours, 2) if flight_time_hours is not None else None,
                    "percent_match_airport": round(airport_percent, 3),
                    "percent_match_flight": round(flight_percent, 3),
                    "percent_match_total": round(total_percent, 3),
                    "airport_scores": (
                        ranked_flight.destination_airport_rank.scores
                        if ranked_flight.destination_airport_rank is not None
                        else None
                    ),
                    "flight_scores": ranked_flight.scores,
                    "departure_scheduled": ranked_flight.flight.raw_result.departure.scheduled,
                    "arrival_scheduled": ranked_flight.flight.raw_result.arrival.scheduled,
                }
            )

        combined_results.sort(key=lambda x: x["percent_match_total"], reverse=True)
        limited_results = combined_results[:limit]

        for idx, row in enumerate(limited_results, start=1):
            row["rank"] = idx

        return jsonify(
            {
                "status": "ok",
                "count": len(limited_results),
                "results": limited_results,
                "active_score_keys": {
                    "airport": sorted(airport_rank.active_score_keys),
                    "flight": sorted(flight_rank.active_score_keys),
                },
            }
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
