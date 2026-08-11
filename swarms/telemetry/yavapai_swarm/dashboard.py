"""
FastAPI + HTMX glassmorphism dashboard for the Yavapai Swarm.
Modeled directly on glass-x patterns (base.html, partials, HTMX swaps, live scoring feel).

This is a stub. Full implementation in Phase 6 (addresses the C comment feedback).
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from .report import generate_activation_report
from .ingestors.base import get_eia_key

app = FastAPI(title="Yavapai 13-Signal Swarm — TELEMETRY_SWARM_V5")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Ensure templates dir exists even in stub
(BASE_DIR / "templates").mkdir(exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Default to real data in the web UI (the "non-simulated" experience)
    report = generate_activation_report(use_real=True)
    report_dict = report.model_dump(mode="json")

    has_eia_key = bool(get_eia_key())

    context = {
        "request": request,
        "title": "Yavapai Swarm v5 — Real Data Mode",
        "coupled_anomalies": report_dict.get("coupled_anomalies", []),
        "agents": report_dict.get("agents", {}),
        "summary": report_dict.get("summary", {}),
        "real_data_summary": report_dict.get("real_data_summary"),
        "has_eia_key": has_eia_key,
        "note": "NON-SIMULATED — Live public telemetry (OpenSky + USGS). Private signals have no public source.",
    }
    return templates.TemplateResponse("index.html", context)


@app.get("/api/report", response_class=JSONResponse)
async def api_report():
    """Always returns the current activation JSON (the primary deliverable)."""
    report = generate_activation_report()
    return report.model_dump(mode="json")


@app.get("/health")
async def health():
    return {"status": "ok", "swarm": "TELEMETRY_SWARM_V5"}
