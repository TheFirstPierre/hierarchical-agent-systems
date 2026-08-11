"""
Report generation for activation — now supports REAL DATA PRIMARY mode.
"""
from datetime import datetime, timezone, timedelta
from .models import SwarmReport, CoupledAnomaly, Anomaly
from .real_collector import RealDataCollector
from .config import SIGNALS
from .real_collector import NO_PUBLIC_REAL_SOURCES  # re-exported for convenience
from .agents.adaptive_seeds import AdaptiveSeedEngine
from .swarm_seeds import DEFAULT_SWARM_SEEDS, YAVAPAI_REGISTRY_ID, seeds_from_coupling_rules


def _swarm_seed_engine() -> AdaptiveSeedEngine:
    base = DEFAULT_SWARM_SEEDS + seeds_from_coupling_rules()
    return AdaptiveSeedEngine(registry_id=YAVAPAI_REGISTRY_ID, base_seeds=base)


def generate_activation_report(
    mode: str = "expert",
    seed: int = 42,
    window: str = "6h",
    use_real: bool = False,
) -> SwarmReport:
    """
    When use_real=True: attempts live fetches for every signal that has a public ingestor.
    Private signals are explicitly marked as having no public real source.
    """
    now = datetime.now(timezone.utc)
    seed_engine = _swarm_seed_engine()
    active_seeds = seed_engine.get_active_seeds(limit=15)

    if not use_real:
        # Original stub behavior (synthetic illustration)
        coupled = CoupledAnomaly(
            coupling_id=f"CPL-{now.strftime('%Y%m%d')}-001",
            involved_clusters=["TESSA", "VECTOR"],
            signals=[4, 12],
            severity=0.81,
            first_seen=now - timedelta(minutes=38),
            last_seen=now - timedelta(minutes=4),
            hypothesis="EHV load spike temporally aligned with automated haulage telemetry surge at Bagdad Mine (cross-check 04_vs_12_09) — ILLUSTRATIVE (synthetic)",
            evidence={
                "04": {"peak_z": 2.8, "ts": (now - timedelta(minutes=22)).isoformat()},
                "12": {"peak_z": 2.4, "ts": (now - timedelta(minutes=19)).isoformat()},
                "correlation": 0.79,
                "window_overlap_sec": 2280,
            },
            cross_check="04_vs_12_09",
        )
        report = SwarmReport(
            mode=mode.upper(),
            window={"start": (now - timedelta(hours=6)).isoformat(), "end": now.isoformat(), "duration": window},
            agents={
                "ECHO": {"status": "NOMINAL", "anomalies": 0},
                "TESSA": {"status": "ELEVATED", "anomalies": 1},
                "CYBER": {"status": "NOMINAL", "anomalies": 0},
                "VECTOR": {"status": "ELEVATED", "anomalies": 1},
            },
            coupled_anomalies=[coupled],
            per_cluster_anomalies={
                "TESSA": [Anomaly(signal_id=4, ts=now - timedelta(minutes=22), severity=0.88, detector="zscore", reason="Load exceeded +2.2σ (synthetic)")],
                "VECTOR": [Anomaly(signal_id=12, ts=now - timedelta(minutes=19), severity=0.79, detector="rate", reason="Haul rate +68% (synthetic)")],
            },
            cross_checks_performed=[
                {"check": "04_vs_12_09", "result": "COUPLED (illustrative)", "score": 0.81, "signals": [4, 12, 9]},
                {"check": "11_vs_03", "result": "NO_EVIDENCE", "score": 0.21, "signals": [11, 3]},
            ],
            summary={
                "total_signals": 13,
                "coupled_events": 1,
                "highest_severity": 0.81,
                "note": "SYNTHETIC ILLUSTRATIVE DATA — use --real for live public telemetry where available",
                "adaptive_seeds": active_seeds[:8],
                "priority_signals": seed_engine.get_priority_signal_ids(),
            },
            data_sources={"mode": "synthetic"},
        )
        report_dict = report.model_dump(mode="json")
        new_seeds = seed_engine.evolve_from_swarm_report(report_dict)
        report.summary["adaptive_seeds_evolved"] = new_seeds
        report.summary["adaptive_seed_context"] = seed_engine.get_context()
        return report

    # === REAL DATA PATH ===
    priority = seed_engine.get_priority_signal_ids()
    collector = RealDataCollector(window=window, priority_signal_ids=priority)
    collector.collect()   # fetches everything we have ingestors for

    real_summary = collector.get_summary()

    # Build a minimal but honest report from whatever real data we actually got
    coupled: list[CoupledAnomaly] = []
    per_cluster: dict[str, list[Anomaly]] = {}
    cross_checks = []

    # Example: if we got real grid data (04) and real blasting (07), we can note possible correlation later
    has_04 = bool(collector.points.get(4))
    has_07 = bool(collector.points.get(7))
    has_01 = bool(collector.points.get(1))
    has_05 = bool(collector.points.get(5))

    if has_04 and has_07:
        cross_checks.append({
            "check": "04_grid_vs_07_blast",
            "result": "DATA_AVAILABLE_BUT_NO_COUPLING_ENGINE_YET",
            "note": "Both 04 (EIA) and 07 (USGS blasts) have real data in this window",
        })

    # Honest statement about what we could not observe
    unavailable = sorted(list(real_summary.get("signals_without_data", [])) + [s for s in [2,3,6,8,9,10,11,12,13] if s not in collector.points or not collector.points.get(s)])

    report = SwarmReport(
        mode=mode.upper() + " + REAL_DATA",
        window=real_summary["window"],
        agents={
            "ECHO": {"status": "PARTIAL_REAL", "real_signals": [1] if has_01 else [], "unobserved": [2, 3]},
            "TESSA": {"status": "PARTIAL_REAL", "real_signals": [s for s in [4,5,7] if collector.points.get(s)], "unobserved": [6]},
            "CYBER": {"status": "NO_PUBLIC_REAL", "real_signals": [], "unobserved": [8, 9, 10]},
            "VECTOR": {"status": "NO_PUBLIC_REAL", "real_signals": [], "unobserved": [11, 12, 13]},
        },
        coupled_anomalies=coupled,   # none yet — real coupling detection coming next
        per_cluster_anomalies=per_cluster,
        cross_checks_performed=cross_checks,
        summary={
            "total_signals": 13,
            "coupled_events": 0,
            "real_points_collected": real_summary["total_real_points_collected"],
            "signals_with_real_data": real_summary["signals_with_real_data"],
            "signals_without_public_real_source": unavailable,
            "note": "NON-SIMULATED MODE — only public telemetry. Private signals have no real data source.",
            "adaptive_seeds": active_seeds[:8],
            "priority_signals": priority,
        },
        data_sources={str(k): v for k, v in real_summary["provenance"].items()},
        real_data_summary=real_summary,
        real_telemetry=real_summary.get("real_telemetry"),  # type: ignore
    )
    report_dict = report.model_dump(mode="json")
    new_seeds = seed_engine.evolve_from_swarm_report(report_dict)
    report.summary["adaptive_seeds_evolved"] = new_seeds
    report.summary["adaptive_seed_context"] = seed_engine.get_context()
    return report
