# MiddleGround: Frontend + Flask Backend (Localhost Setup)

This project is set up for a split local architecture:

- Frontend (HTML/CSS/JS) runs on one port (example: `http://localhost:5500`)
- Flask backend API runs on another port (`http://127.0.0.1:5001`)

The frontend makes HTTP requests to Flask and receives JSON responses.

## Ports

In local development, frontend and backend are usually separate processes, so they run on different ports.

Example:
- Frontend: `5500`
- Backend: `5001`

Because origins differ by port, CORS must allow frontend origin(s).  
`backend/app.py` uses `flask-cors` to allow:

- `http://localhost:5500`
- `http://127.0.0.1:5500`

## Setup

### 1) Install Python dependencies

From project root:

```bash
python3 -m pip install -r backend/requirements.txt
```

### 2) Start Flask backend

```bash
python3 backend/app.py
```

Backend will run at:

`http://127.0.0.1:5001`

### 3) Start frontend

Serve `main.html` with any local static server (for example VS Code Live Server) on port `5500`:

`http://127.0.0.1:5500/main.html` or `http://localhost:5500/main.html`

## API Endpoints

### Health check

```http
GET /api/health
```

Example response:

```json
{
  "status": "ok",
  "message": "Flask server is running"
}
```

### Compute endpoint

```http
GET /api/compute?value=5
```

Behavior:
- Requires `value >= 1`
- Returns sum of squares from `1..value`

Example response:

```json
{
  "description": "Sum of squares from 1..value",
  "input": 5,
  "result": 55
}
```
