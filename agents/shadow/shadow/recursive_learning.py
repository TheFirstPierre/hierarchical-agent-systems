"""
Recursive loop learning for SHADOW agent.

Each turn/cycle absorbs findings into a persistent learning store that feeds
back into subsequent turns: enriched seeds, boosted terms, signal weights,
ADS-B trend history, and cycle summaries. Seed evolution delegated to AdaptiveSeedEngine.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .adaptive_seeds import AdaptiveSeedEngine

LEARNING_PATH = Path(__file__).resolve().parents[1] / "data" / "shadow_recursive_learnings.json"
SHADOW_REGISTRY_ID = "shadow-regional-anomaly-monitor-2026"


class RecursiveLearningStore:
    def __init__(self, mission_id: str, base_seeds: list[str] | None = None):
        self.mission_id = mission_id
        self.data: dict[str, Any] = self._load()
        from .targets import DEFAULT_SEEDS
        self._seed_engine = AdaptiveSeedEngine(
            registry_id=mission_id or SHADOW_REGISTRY_ID,
            base_seeds=base_seeds or list(DEFAULT_SEEDS),
            registry_path=LEARNING_PATH.parent / "adaptive_seed_registry.json",
        )

    def _load(self) -> dict[str, Any]:
        if LEARNING_PATH.exists():
            try:
                all_data = json.loads(LEARNING_PATH.read_text())
                return all_data.get(self.mission_id, self._empty())
            except (json.JSONDecodeError, OSError):
                pass
        return self._empty()

    def _empty(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "cycles_completed": 0,
            "turns_absorbed": 0,
            "learned_seeds": [],
            "boosted_terms": {},
            "reinforced_signals": {},
            "adsb_history": {"ksez": [], "prc": []},
            "useful_patterns": [],
            "known_finding_keys": [],
            "cycle_log": [],
            "last_updated": None,
        }

    def get_known_finding_keys(self) -> set[str]:
        keys = set(self.data.get("known_finding_keys", []))
        keys.add("triple_stack_baseline")
        for p in self.data.get("useful_patterns", []):
            if p.get("id"):
                keys.add(p["id"])
        return keys

    def record_finding_key(self, key: str) -> None:
        if not key:
            return
        known = self.data.setdefault("known_finding_keys", [])
        if key not in known:
            known.append(key)
        self.data["known_finding_keys"] = known[-100:]

    def save(self) -> None:
        LEARNING_PATH.parent.mkdir(parents=True, exist_ok=True)
        all_data: dict[str, Any] = {}
        if LEARNING_PATH.exists():
            try:
                all_data = json.loads(LEARNING_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                all_data = {}
        self.data["learned_seeds"] = self._seed_engine.get_active_seeds(limit=30)
        self.data["adaptive_seeds"] = self._seed_engine.get_context()
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        all_data[self.mission_id] = self.data
        LEARNING_PATH.write_text(json.dumps(all_data, indent=2, default=str))
        self._seed_engine.save()

    def absorb_turn(
        self,
        turn: int,
        phase: str,
        findings: list[dict[str, Any]],
        expanded_terms: list[dict[str, Any]],
        correlation: dict[str, Any],
        adsb_ksez: dict[str, Any] | None,
        adsb_prc: dict[str, Any] | None,
        web_intel: list[dict[str, Any]] | None = None,
        active_seeds: list[str] | None = None,
    ) -> dict[str, Any]:
        """Absorb one turn's output; return learning delta for this turn."""
        delta: dict[str, Any] = {"turn": turn, "phase": phase, "new_seeds": [], "boosted": []}
        self.data["turns_absorbed"] += 1

        if active_seeds:
            self._seed_engine.record_usage(active_seeds)

        for term_obj in expanded_terms:
            term = term_obj.get("term", "")
            score = term_obj.get("score", 0)
            if not term or score < 2.0:
                continue
            prev = self.data["boosted_terms"].get(term, 0)
            new_score = max(prev, score)
            if new_score > prev:
                self.data["boosted_terms"][term] = new_score
                delta["boosted"].append(term)

        for sig in correlation.get("signals", []):
            self.data["reinforced_signals"][sig] = self.data["reinforced_signals"].get(sig, 0) + 1

        if adsb_ksez:
            self._record_adsb("ksez", adsb_ksez)
        if adsb_prc:
            self._record_adsb("prc", adsb_prc)

        for f in findings:
            if f.get("type") == "useful_discovery":
                pattern = {"turn": turn, "id": f.get("id"), "ts": datetime.now(timezone.utc).isoformat()}
                self.data["useful_patterns"].append(pattern)
                if active_seeds:
                    self._seed_engine.record_discovery(active_seeds, severity=0.9)

        new_seeds = self._seed_engine.evolve_from_turn(
            turn=turn,
            phase=phase,
            expanded_terms=expanded_terms,
            correlation=correlation,
            findings=findings,
            web_intel=web_intel,
            adsb=adsb_ksez,
        )
        delta["new_seeds"] = new_seeds
        self.data["learned_seeds"] = self._seed_engine.get_active_seeds(limit=30)

        return delta

    def _record_adsb(self, key: str, snapshot: dict[str, Any]) -> None:
        hist = self.data["adsb_history"][key]
        hist.append({
            "ts": snapshot.get("ts"),
            "count": snapshot.get("aircraft_count", 0),
            "low_alt": snapshot.get("low_altitude_under_8000ft", 0),
            "mil": snapshot.get("non_ga_callsigns", 0),
        })
        self.data["adsb_history"][key] = hist[-50:]

    def complete_cycle(self, cycle: int, useful_count: int, top_correlation: float) -> dict[str, Any]:
        """Mark end of a full phase rotation; persist cycle summary and evolve seeds."""
        self.data["cycles_completed"] = cycle
        ksez_trend = self._adsb_trend("ksez")
        prc_trend = self._adsb_trend("prc")
        context = {
            "top_boosted_terms": sorted(
                self.data["boosted_terms"].items(), key=lambda x: -x[1]
            )[:8],
            "reinforced_signals": dict(
                sorted(self.data["reinforced_signals"].items(), key=lambda x: -x[1])[:10]
            ),
            "adsb_trend": {"ksez": ksez_trend, "prc": prc_trend},
        }
        cycle_new_seeds = self._seed_engine.evolve_from_cycle(cycle, context)
        self.data["learned_seeds"] = self._seed_engine.get_active_seeds(limit=30)

        summary = {
            "cycle": cycle,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "learned_seeds_count": len(self.data["learned_seeds"]),
            "new_seeds_this_cycle": cycle_new_seeds,
            "top_boosted_terms": context["top_boosted_terms"],
            "reinforced_signals": context["reinforced_signals"],
            "useful_findings_so_far": useful_count,
            "top_correlation": top_correlation,
            "adsb_trend": context["adsb_trend"],
            "adaptive_seed_context": self._seed_engine.get_context(),
        }
        self.data["cycle_log"].append(summary)
        self.data["cycle_log"] = self.data["cycle_log"][-20:]
        self.save()
        return summary

    def _adsb_trend(self, key: str) -> dict[str, Any]:
        hist = self.data["adsb_history"].get(key, [])
        if len(hist) < 2:
            return {"delta": 0, "samples": len(hist), "latest": hist[-1]["count"] if hist else 0}
        latest = hist[-1]["count"]
        prev = hist[-2]["count"]
        return {"delta": latest - prev, "samples": len(hist), "latest": latest, "peak": max(h["count"] for h in hist)}

    def get_enriched_seeds(self, base_seeds: list[str]) -> list[str]:
        """Merge base seeds with adaptively evolved seeds (deduplicated, fitness-ranked)."""
        engine_seeds = self._seed_engine.get_active_seeds(limit=25)
        merged = list(base_seeds)
        for s in engine_seeds:
            if s not in merged:
                merged.append(s)
        for s in self.data.get("learned_seeds", []):
            if s not in merged:
                merged.append(s)
        return merged[:30]

    def get_learning_context(self) -> dict[str, Any]:
        return {
            "cycles_completed": self.data["cycles_completed"],
            "turns_absorbed": self.data["turns_absorbed"],
            "learned_seeds": self.data["learned_seeds"][-10:],
            "adaptive_seeds": self._seed_engine.get_context(),
            "top_boosted_terms": sorted(self.data["boosted_terms"].items(), key=lambda x: -x[1])[:10],
            "reinforced_signals": self.data["reinforced_signals"],
            "adsb_trends": {
                "ksez": self._adsb_trend("ksez"),
                "prc": self._adsb_trend("prc"),
            },
            "cycle_log": self.data["cycle_log"][-5:],
        }

    def synthesize_cycle_insight(self, cycle: int) -> dict[str, Any] | None:
        """Generate a learned insight from accumulated recursive state."""
        trends = self.get_learning_context()["adsb_trends"]
        top_terms = sorted(self.data["boosted_terms"].items(), key=lambda x: -x[1])[:5]
        top_sigs = sorted(self.data["reinforced_signals"].items(), key=lambda x: -x[1])[:5]
        active_seeds = self._seed_engine.get_active_seeds(limit=3)

        if not top_terms and not top_sigs:
            return None

        hypothesis_parts = []
        if top_terms:
            hypothesis_parts.append(
                f"Recursive learning reinforced terms: {', '.join(t for t, _ in top_terms)}"
            )
        if top_sigs:
            hypothesis_parts.append(
                f"Reinforced signals across {cycle} cycles: {', '.join(s for s, _ in top_sigs)}"
            )
        if trends["ksez"].get("delta", 0) != 0:
            hypothesis_parts.append(f"KSEZ ADS-B delta since last sample: {trends['ksez']['delta']:+d}")
        if trends["prc"].get("latest", 0) > 0:
            hypothesis_parts.append(f"Prescott VOR corridor active ({trends['prc']['latest']} aircraft)")

        severity = min(0.97, 0.75 + 0.03 * cycle + 0.02 * len(top_terms))
        return {
            "category": "RECURSIVE_LEARNED_INSIGHT",
            "severity": round(severity, 2),
            "title": f"Cycle {cycle} Adaptive Seed Synthesis",
            "hypothesis": ". ".join(hypothesis_parts),
            "actionable_insights": [
                f"Prioritize evolved seed: {active_seeds[0]}" if active_seeds else "Expand seed set",
                f"Watch KSEZ trend (peak {trends['ksez'].get('peak', 0)} aircraft)" if trends["ksez"].get("samples") else "Continue ADS-B sampling",
                "Cross-check reinforced signals against PURSUE war.gov/ufo Arizona entries",
            ],
            "cycle": cycle,
            "learning_context": self.get_learning_context(),
        }