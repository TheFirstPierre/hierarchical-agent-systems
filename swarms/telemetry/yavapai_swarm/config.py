"""
Configuration and thresholds for the 13-Signal Yavapai Swarm.
All values are tunable; real deployments would load from YAML.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SignalDef:
    id: int
    name: str
    cluster: str
    unit: str
    normal_range: tuple[float, float]
    anomaly_threshold: float  # z-score or absolute depending on detector


# Canonical 13 signals
SIGNALS: dict[int, SignalDef] = {
    1: SignalDef(1, "ADS-B High-Altitude (Prescott VOR)", "ECHO", "aircraft/hr", (8, 45), 2.5),
    2: SignalDef(2, "Low-Altitude Training Density", "ECHO", "squawks/hr", (25, 120), 2.0),
    3: SignalDef(3, "Atmospheric RF Link (Towers Mtn ↔ Crown King)", "ECHO", "dBm", (-68, -52), 1.8),
    4: SignalDef(4, "EHV Load-Balance (APS 345/500 kV)", "TESSA", "MW", (3200, 5200), 2.2),
    5: SignalDef(5, "Verde Watershed Flow (USGS)", "TESSA", "cfs", (180, 850), 2.0),
    6: SignalDef(6, "Logistics Artery (I-17 / US-93)", "TESSA", "events/hr", (4, 22), 1.9),
    7: SignalDef(7, "Industrial Blasting (Drake/Jerome)", "TESSA", "events/day", (0, 9), 2.3),
    8: SignalDef(8, "Municipal API Health (CIIACC/Sheriff)", "CYBER", "score", (0.85, 1.0), 1.7),
    9: SignalDef(9, "P25 Trunking / Dispatch Volume", "CYBER", "incidents/hr", (18, 65), 2.1),
    10: SignalDef(10, "Supply Chain Vetting (AZ Munis)", "CYBER", "leak_score", (0.0, 0.15), 2.0),
    11: SignalDef(11, "NDVI Fire-Watch (Prescott NF)", "VECTOR", "index", (0.42, 0.68), 1.6),
    12: SignalDef(12, "Mining Automation (Bagdad AHS)", "VECTOR", "hauls/hr", (38, 95), 2.4),
    13: SignalDef(13, "Population Drift (Whiskey Row / Verde)", "VECTOR", "delta", (-0.8, 0.8), 1.8),
}

CLUSTERS = ["ECHO", "TESSA", "CYBER", "VECTOR"]

# Explicit cross-domain rules from the activation directive
EXPLICIT_COUPLING_RULES = [
    {
        "id": "04_vs_12_09",
        "name": "Grid Spike ↔ Mining + Emergency",
        "signals": [4, 12, 9],
        "clusters": ["TESSA", "VECTOR", "CYBER"],
        "condition": "If 04 spikes, check whether 12 or 09 mirror the deviation within time window",
    },
    {
        "id": "11_vs_03",
        "name": "Fire Risk ↔ RF Degradation",
        "signals": [11, 3],
        "clusters": ["VECTOR", "ECHO"],
        "condition": "If 11 indicates high fire risk (sustained low NDVI), check for 03 RF link degradation",
    },
]


@dataclass
class SwarmConfig:
    window_minutes: int = 360  # 6 hours default
    coupling_severity_threshold: float = 0.65
    coincident_window_minutes: int = 45
    seed: int = 42
    real_ingestors_enabled: bool = True
    # Permission model for sensitive actions (real data collection, key management, etc.)
    # "always ask" = default interactive safe mode (prompts before external calls / writes)
    # Other future values could be "ask once", "trusted", etc.
    permission: str = "always ask"
    # Per-signal overrides could go here in real YAML
    thresholds: dict[int, dict[str, Any]] = field(default_factory=dict)


DEFAULT_CONFIG = SwarmConfig()

# Signals that currently have no usable public real-time data source
NO_PUBLIC_REAL_SOURCES = {2, 3, 6, 8, 9, 10, 11, 12, 13}


# --- Persistent Config Handling ---

import os
from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = CONFIG_DIR / "swarm_config.yaml"


def load_config() -> SwarmConfig:
    """Load SwarmConfig from disk (YAML). Falls back to DEFAULT_CONFIG."""
    if not CONFIG_PATH.exists():
        return SwarmConfig()

    try:
        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}
        # Only override known fields for safety
        cfg = SwarmConfig()
        for field_name in ["window_minutes", "coupling_severity_threshold",
                           "coincident_window_minutes", "seed",
                           "real_ingestors_enabled", "permission", "thresholds"]:
            if field_name in data:
                setattr(cfg, field_name, data[field_name])
        return cfg
    except Exception:
        # On any parse error, return safe defaults
        return SwarmConfig()


def save_config(cfg: SwarmConfig) -> None:
    """Persist (parts of) the config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Only persist the fields we want user-tunable
    data = {
        "permission": cfg.permission,
        "window_minutes": cfg.window_minutes,
        "real_ingestors_enabled": cfg.real_ingestors_enabled,
        # Add more as needed
    }
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)


# Global loaded config (can be reloaded)
CURRENT_CONFIG = load_config()

# Ensure a config file exists on first use so users can see/edit it easily
if not CONFIG_PATH.exists():
    save_config(CURRENT_CONFIG)
