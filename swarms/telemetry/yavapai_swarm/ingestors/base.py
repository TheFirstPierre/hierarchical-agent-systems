"""
Real Data Ingestors Base — TELEMETRY_SWARM_V5

Non-simulated path. Every point produced here carries explicit provenance.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from pydantic import BaseModel

from ..models import TelemetryPoint


class IngestorError(Exception):
    """Raised when a real data source cannot be fetched (timeout, auth, rate limit, etc.)."""


class RealIngestor(ABC):
    """Base for all real/public data ingestors."""

    signal_id: int
    name: str
    source_type: str = "real"   # "real" | "proxy"

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "yavapai-swarm/5.0 (local research tool)"},
            follow_redirects=True,
        )

    @abstractmethod
    def fetch(self, start: datetime, end: datetime) -> list[TelemetryPoint]:
        """
        Return time-ordered TelemetryPoints for the closed interval [start, end].
        Must set .source = "real" or "proxy" on every point.
        Should raise IngestorError (or subclass) on hard failure after retries.
        """
        ...

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def window_from_spec(spec: str | int) -> tuple[datetime, datetime]:
    """
    Accepts "6h", "24h", "2d", or integer minutes.
    Returns (start, end) in UTC.
    """
    end = utc_now()
    if isinstance(spec, int):
        delta = timedelta(minutes=spec)
    else:
        spec = spec.lower().strip()
        if spec.endswith("h"):
            delta = timedelta(hours=int(spec[:-1]))
        elif spec.endswith("d"):
            delta = timedelta(days=int(spec[:-1]))
        elif spec.endswith("m"):
            delta = timedelta(minutes=int(spec[:-1]))
        else:
            delta = timedelta(hours=6)
    return end - delta, end


def get_eia_key() -> str | None:
    """EIA API key from env (preferred) or data/eia_key.txt"""
    key = os.environ.get("EIA_API_KEY")
    if key:
        return key
    key_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "eia_key.txt")
    if os.path.exists(key_file):
        with open(key_file) as f:
            return f.read().strip() or None
    return None


def save_eia_key(key: str):
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "..", "data"), exist_ok=True)
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "eia_key.txt")
    with open(path, "w") as f:
        f.write(key.strip())
    os.chmod(path, 0o600)
