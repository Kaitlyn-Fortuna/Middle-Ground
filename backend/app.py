from flask import Flask, jsonify, request
from flask_cors import CORS

from parseFilters import (
    parse_filters_api_json
)
from rankFilters import (
    format_rank_results,
    import_airport_data,
    initialize_ranked_airports,
    overall_rank,
    run_all_ranks,
)


app = Flask(__name__)

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





if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
