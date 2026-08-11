"""
Project Glass X - Main FastAPI application

Local-only web UI for X scheduling + the famous Virality Matrix.
"""

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app.database import init_db, get_setting, set_setting, create_scheduled_post, get_upcoming_posts
from app.virality import score_post
from app.scheduler import start_scheduler, shutdown_scheduler
from app.x_client import verify_credentials

load_dotenv()

# --- Lifespan: DB + Scheduler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Project Glass X", lifespan=lifespan)
BASE_DIR = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Custom filter so templates can parse JSON stored in the DB
def fromjson_filter(value: str):
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return value

templates.env.filters["fromjson"] = fromjson_filter


# --------------------------- Helpers ---------------------------

def get_x_status() -> dict[str, Any]:
    creds = {
        "X_API_KEY": os.getenv("X_API_KEY"),
        "X_API_SECRET": os.getenv("X_API_SECRET"),
        "X_ACCESS_TOKEN": os.getenv("X_ACCESS_TOKEN"),
        "X_ACCESS_SECRET": os.getenv("X_ACCESS_SECRET"),
    }
    has_keys = all(creds.values())
    if not has_keys:
        return {"connected": False, "message": "No API keys configured"}

    result = verify_credentials()
    if result.get("ok"):
        return {
            "connected": True,
            "username": result.get("username"),
            "name": result.get("name"),
            "followers": result.get("followers"),
        }
    return {"connected": False, "message": result.get("error", "Invalid credentials")}


# --------------------------- Routes ---------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    x_status = get_x_status()
    upcoming = get_upcoming_posts(limit=8)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "x_status": x_status,
            "upcoming": upcoming,
            "active_tab": "compose",
        },
    )


@app.get("/compose", response_class=HTMLResponse)
async def compose_page(request: Request):
    x_status = get_x_status()
    return templates.TemplateResponse(
        "partials/compose.html",
        {"request": request, "x_status": x_status},
    )


@app.post("/api/score")
async def api_score(
    text: str = Form(...),
    has_media: bool = Form(False),
    is_thread: bool = Form(False),
):
    """Live virality scoring endpoint (called via HTMX on every keystroke)."""
    result = score_post(text=text, has_media=has_media, is_thread=is_thread)
    return JSONResponse({
        "total": result.total,
        "grade": result.grade,
        "grade_explanation": result.explain_grade(result.grade) if hasattr(result, 'explain_grade') else "",
        "breakdown": result.breakdown,
        "suggestions": result.suggestions,
        "boost": result.predicted_engagement_boost,
    })


@app.post("/api/schedule")
async def api_schedule(
    text: str = Form(...),
    scheduled_at: str = Form(...),   # "2025-06-01T14:30"
    has_media: bool = Form(False),
):
    """Schedule a post (MVP: single tweet for now)."""
    if not text.strip():
        return JSONResponse({"error": "Text is required"}, status_code=400)

    # Parse datetime (naive for MVP; assume local time)
    try:
        dt = datetime.fromisoformat(scheduled_at)
    except ValueError:
        return JSONResponse({"error": "Invalid date format"}, status_code=400)

    # Score it at schedule time
    score_result = score_post(text=text, has_media=has_media)

    content = json.dumps([{"text": text.strip()}])  # thread-ready structure

    post_id = create_scheduled_post(
        content_json=content,
        scheduled_at=dt.isoformat(),
        media_paths_json="[]" if not has_media else None,
        virality_score=score_result.total,
        virality_grade=score_result.grade,
    )

    return JSONResponse({
        "success": True,
        "id": post_id,
        "scheduled_for": dt.isoformat(),
        "virality": score_result.total,
    })


@app.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    upcoming = get_upcoming_posts(limit=30)
    return templates.TemplateResponse(
        "partials/queue.html",
        {"request": request, "upcoming": upcoming},
    )


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics dashboard (currently shows placeholders + how to unlock real data)."""
    x_status = get_x_status()
    return templates.TemplateResponse(
        "partials/analytics.html",
        {"request": request, "x_status": x_status},
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    x_status = get_x_status()

    # Detect common hosting platforms
    is_hosted = bool(
        os.getenv("RENDER") or
        os.getenv("RAILWAY_ENVIRONMENT") or
        os.getenv("FLY_APP_NAME") or
        os.getenv("HOSTED_MODE")
    )

    return templates.TemplateResponse(
        "partials/settings.html",
        {
            "request": request,
            "x_status": x_status,
            "is_hosted": is_hosted,
        },
    )


@app.post("/api/settings/keys")
async def save_keys(
    api_key: str = Form(...),
    api_secret: str = Form(...),
    access_token: str = Form(...),
    access_secret: str = Form(...),
):
    """
    Local-only convenience: writes keys to .env for local development.
    For any real deployment (Render, Railway, etc.), set the four
    X_* environment variables directly in the hosting platform dashboard instead.
    This endpoint will still work for local testing.
    """
    env_path = Path(__file__).parent.parent / ".env"
    lines = [
        "# Project Glass X - X API Credentials (local only)",
        f"X_API_KEY={api_key.strip()}",
        f"X_API_SECRET={api_secret.strip()}",
        f"X_ACCESS_TOKEN={access_token.strip()}",
        f"X_ACCESS_SECRET={access_secret.strip()}",
    ]
    try:
        env_path.write_text("\n".join(lines))
        os.environ["X_API_KEY"] = api_key.strip()
        os.environ["X_API_SECRET"] = api_secret.strip()
        os.environ["X_ACCESS_TOKEN"] = access_token.strip()
        os.environ["X_ACCESS_SECRET"] = access_secret.strip()
        test = verify_credentials()
        return JSONResponse({"saved": True, "test": test, "mode": "local"})
    except Exception as e:
        return JSONResponse({
            "saved": False,
            "error": "Could not write .env (common in hosted environments). Set env vars on the platform instead.",
            "details": str(e)
        }, status_code=400)


@app.post("/api/test-connection")
async def test_connection():
    result = verify_credentials()
    return JSONResponse(result)


@app.post("/api/trigger-posting")
async def trigger_posting():
    """
    Endpoint that can be called by external cron services (cron-job.org, GitHub Actions, etc.)
    to wake the app and force the scheduler to check for due posts.
    This is the recommended way to get reliable scheduling on free hosting tiers
    that spin down after inactivity.
    """
    from app.scheduler import check_and_post_due_items
    try:
        check_and_post_due_items()
        return {"triggered": True, "message": "Posting check executed"}
    except Exception as e:
        return JSONResponse({"triggered": False, "error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    """Simple health check for monitoring / uptime services."""
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# Simple health / status
@app.get("/api/status")
async def status():
    return {
        "ok": True,
        "x_connected": get_x_status()["connected"],
        "time": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
