"""
regional multi-domain anomaly anomaly mission profile for SHADOW agent.
"""
from __future__ import annotations

DEFAULT_MISSION_ID = "shadow-regional-anomaly-monitor-2026"

# Seed queries from prior SESP Sedona campaigns
DEFAULT_SEEDS = [
    "Sedona Arizona military activity",
    "KSEZ Black Hawk overflight May 2026",
    "Sedona anomaly military sensor correlation",
    "Yavapai County MTR IR-112 Sedona",
    "Luke AFB low-level training routes northern Arizona",
    "Secret Mountain Wilderness military overflights",
    "PURSUE anomaly Release CENTCOM orbs military",
]

# KSEZ / Sedona area ADS-B bounding box
KSEZ_BBOX = {
    "lamin": 34.70,
    "lomin": -112.00,
    "lamax": 35.00,
    "lomax": -111.60,
    "center": "KSEZ Sedona Airport",
}

# Substantial discovery thresholds
DISCOVERY_THRESHOLDS = {
    "novel_term_score": 4.0,
    "novel_term_count_at_3": 3,
    "correlation_score": 0.72,
    "adsb_elevated_count": 8,
    "memory_importance": 0.85,
}

# Known baseline for Sedona area low-alt military training noise
ADS_B_BASELINE_AIRCRAFT = 4