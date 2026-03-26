from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.parseFilters import SearchFilters, load_filters_json, parse_filters_json


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


@app.get("/api/compute")
def compute():
    value = request.args.get("value", default=10, type=int)

    if value < 1:
        return jsonify({"error": "value must be >= 1"}), 400

    result = sum(i * i for i in range(1, value + 1))

    return jsonify(
        {
            "input": value,
            "result": result,
            "description": "Sum of squares from 1..value",
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
