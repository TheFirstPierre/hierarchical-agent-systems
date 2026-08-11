# Glass X — Local X Composition Tool

Local FastAPI + HTMX application for draft scoring and scheduling against the X platform.

## Features

- Offline **virality matrix** (explainable factor scores)
- Local SQLite storage
- Optional X API credentials via environment
- Scheduler worker for queued posts

## Quick start

```bash
cd tools/glass-x
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000

Copy `.env.example` to `.env` for API credentials. Local DB files are gitignored.
