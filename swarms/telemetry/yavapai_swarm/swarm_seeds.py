"""Default discovery seeds for the Yavapai 13-signal swarm."""
from __future__ import annotations

from .config import SIGNALS, EXPLICIT_COUPLING_RULES

YAVAPAI_REGISTRY_ID = "yavapai-13-signal-swarm-2026"

DEFAULT_SWARM_SEEDS = [
    "Yavapai ECHO cluster ADS-B Prescott VOR training density anomaly",
    "TESSA grid load EHV 345kV spike coupled mining haulage Bagdad",
    "Verde watershed USGS flow deviation fire season cross-check",
    "CYBER P25 dispatch volume municipal API health Yavapai County",
    "VECTOR NDVI fire-watch Prescott NF RF link degradation coupling",
    "Industrial blasting Drake Jerome correlated grid emergency response",
    "I-17 logistics artery incident surge northern Arizona",
    "13-signal cross-domain coupling 04_vs_12_09 rule verification",
]

# Map coupling rules to seed queries for recurring evolution
COUPLING_SEED_TEMPLATES = [
    "{name}: monitor signals {signals} within coincident window",
    "Deep cross-check {id} clusters {clusters} Yavapai operational",
]


def seeds_from_coupling_rules() -> list[str]:
    out: list[str] = []
    for rule in EXPLICIT_COUPLING_RULES:
        out.append(
            f"Yavapai {rule['name']} signals {rule['signals']} cross-domain watch"
        )
    return out


def signal_seed(signal_id: int) -> str:
    sig = SIGNALS.get(signal_id)
    if not sig:
        return f"Yavapai signal {signal_id} anomaly depth"
    return f"Yavapai signal {signal_id:02d} {sig.name} {sig.cluster} cluster monitoring"