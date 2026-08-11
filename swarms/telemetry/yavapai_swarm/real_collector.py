"""
RealDataCollector — Non-simulated data acquisition for the 13-Signal Swarm.

This is the primary path when the user requests "real data".
It only returns what we can actually fetch from public sources right now.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .config import SIGNALS
from .ingestors.base import RealIngestor, window_from_spec, IngestorError
from .ingestors.usgs_water import USGSWaterIngestor
from .ingestors.usgs_blast import USGSBlastIngestor
from .ingestors.opensky_adsb import OpenSkyADSBIngestor
from .ingestors.eia_grid import EIAGridIngestor
from .models import TelemetryPoint


# Mapping from signal_id to ingestor class (only the ones we have real implementations for)
REAL_INGESTOR_CLASSES: dict[int, type[RealIngestor]] = {
    1: OpenSkyADSBIngestor,   # ADS-B
    4: EIAGridIngestor,       # Grid load proxy
    5: USGSWaterIngestor,     # Verde flow
    7: USGSBlastIngestor,     # Blasting
}

# Signals that have *no* public real-time source we can use today
NO_PUBLIC_REAL_SOURCES = {2, 3, 6, 8, 9, 10, 11, 12, 13}

# Re-export for other modules
__all__ = ["RealDataCollector", "NO_PUBLIC_REAL_SOURCES", "REAL_INGESTOR_CLASSES"]


class RealDataCollector:
    def __init__(self, window: str = "6h", priority_signal_ids: list[int] | None = None):
        self.window_spec = window
        self.start: datetime
        self.end: datetime
        self.start, self.end = window_from_spec(window)
        self.priority_signal_ids = priority_signal_ids or []
        self.points: dict[int, list[TelemetryPoint]] = {}
        self.errors: dict[int, str] = {}
        self.provenance: dict[int, str] = {}

    def collect(self, signal_ids: list[int] | None = None) -> dict[int, list[TelemetryPoint]]:
        """
        Attempt to fetch real data for all (or specified) signals that have ingestors.
        Returns mapping signal_id -> list of points (possibly empty on failure).
        """
        if signal_ids is None:
            signal_ids = list(REAL_INGESTOR_CLASSES.keys())

        if self.priority_signal_ids:
            ordered = [s for s in self.priority_signal_ids if s in signal_ids]
            ordered += [s for s in signal_ids if s not in ordered]
            signal_ids = ordered

        for sid in signal_ids:
            if sid not in REAL_INGESTOR_CLASSES:
                self.provenance[sid] = "no_public_real_source"
                self.points[sid] = []
                continue

            ingestor_cls = REAL_INGESTOR_CLASSES[sid]
            try:
                with ingestor_cls() as ing:
                    pts = ing.fetch(self.start, self.end)
                    self.points[sid] = pts
                    self.provenance[sid] = ing.source_type
                    if not pts:
                        self.errors[sid] = "No data returned in window"
            except IngestorError as e:
                self.points[sid] = []
                self.errors[sid] = str(e)
                self.provenance[sid] = "fetch_failed"
            except Exception as e:
                self.points[sid] = []
                self.errors[sid] = f"Unexpected error: {e}"
                self.provenance[sid] = "error"

        return self.points

    def get_summary(self) -> dict[str, Any]:
        total_real_points = sum(len(v) for v in self.points.values())
        successful = [sid for sid, pts in self.points.items() if pts]
        failed = list(self.errors.keys())

        return {
            "window": {"start": self.start.isoformat(), "end": self.end.isoformat()},
            "signals_requested": list(self.points.keys()),
            "signals_with_real_data": successful,
            "signals_without_data": failed,
            "total_real_points_collected": total_real_points,
            "provenance": self.provenance,
            "errors": self.errors,
        }

    def to_swarm_report_dict(self) -> dict[str, Any]:
        """Minimal structure that can be merged into SwarmReport."""
        return {
            "real_data_summary": self.get_summary(),
            "real_telemetry": {
                str(sid): [p.model_dump(mode="json") for p in pts]
                for sid, pts in self.points.items()
            },
        }
