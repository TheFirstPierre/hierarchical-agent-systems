"""
Adaptive seed engine — recurring generation, scoring, and pruning of discovery seeds.

Feeds both Yavapai 13-signal swarm and SHADOW tier agent. Seeds evolve from turns,
cycles, swarm activations, telemetry anomalies, and useful findings.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from pathlib import Path

GEO_ANCHORS = [
    "Sedona", "KSEZ", "Yavapai County", "Luke AFB", "Prescott VOR",
    "northern Arizona", "Verde Valley", "Secret Mountain Wilderness",
]
SEED_TEMPLATES = [
    "{anchor} {term} military anomaly correlation",
    "{anchor} {signal} operational anomaly cross-check",
    "Yavapai signal {signal_id} {signal_name} elevated monitoring",
    "{anchor} {tag1} {tag2} federal sensor pipeline",
    "Recursive depth: {terms} over {anchor}",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


class AdaptiveSeedEngine:
    """Persistent adaptive seed registry with fitness-based evolution."""

    def __init__(
        self,
        registry_id: str,
        base_seeds: list[str],
        registry_path: Path | None = None,
        max_active: int = 40,
    ):
        self.registry_id = registry_id
        self.base_seeds = [_normalize(s) for s in base_seeds]
        self.max_active = max_active
        self.registry_path = registry_path or (
            Path(__file__).resolve().parents[2] / "data" / "adaptive_seed_registry.json"
        )
        self.data = self._load()

    def _empty(self) -> dict[str, Any]:
        return {
            "registry_id": self.registry_id,
            "generation": 0,
            "evolution_cycles": 0,
            "records": {},
            "evolution_log": [],
            "last_evolved": None,
        }

    def _load(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            data = self._empty()
            self._bootstrap_records(data)
            return data
        try:
            all_data = json.loads(self.registry_path.read_text())
            reg = all_data.get(self.registry_id, self._empty())
            if not reg.get("records"):
                self._bootstrap_records(reg)
            return reg
        except (json.JSONDecodeError, OSError):
            data = self._empty()
            self._bootstrap_records(data)
            return data

    def _bootstrap_records(self, data: dict[str, Any]) -> None:
        for seed in self.base_seeds:
            self._upsert_record(data, seed, source="base", fitness=1.0, tags=[])

    def save(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        all_data: dict[str, Any] = {}
        if self.registry_path.exists():
            try:
                all_data = json.loads(self.registry_path.read_text())
            except (json.JSONDecodeError, OSError):
                all_data = {}
        self.data["last_evolved"] = _now_iso()
        all_data[self.registry_id] = self.data
        self.registry_path.write_text(json.dumps(all_data, indent=2, default=str))

    def _upsert_record(
        self,
        data: dict[str, Any],
        text: str,
        source: str,
        fitness: float,
        tags: list[str] | None = None,
        parent: str | None = None,
    ) -> bool:
        text = _normalize(text)
        if len(text) < 12 or len(text) > 200:
            return False
        records: dict[str, Any] = data["records"]
        if text in records:
            rec = records[text]
            rec["fitness"] = max(rec.get("fitness", 0), fitness)
            rec["last_touched"] = _now_iso()
            if tags:
                rec["tags"] = list(set(rec.get("tags", []) + tags))[:12]
            return False
        if len(records) >= self.max_active * 2:
            self._prune_inplace(data, keep=self.max_active)
        records[text] = {
            "text": text,
            "source": source,
            "fitness": fitness,
            "created_at": _now_iso(),
            "last_touched": _now_iso(),
            "last_used": None,
            "uses": 0,
            "discoveries": 0,
            "generation": data.get("generation", 0),
            "tags": tags or [],
            "parent": parent,
        }
        return True

    def _prune_inplace(self, data: dict[str, Any], keep: int) -> int:
        records: dict[str, Any] = data["records"]
        base_texts = set(self.base_seeds)
        ranked = sorted(
            records.items(),
            key=lambda kv: (
                kv[1]["text"] in base_texts,
                kv[1].get("discoveries", 0),
                kv[1].get("fitness", 0),
                kv[1].get("uses", 0),
            ),
            reverse=True,
        )
        keep_texts = {t for t, _ in ranked[:keep]}
        keep_texts |= base_texts
        removed = [t for t in records if t not in keep_texts]
        for t in removed:
            del records[t]
        return len(removed)

    def get_active_seeds(self, limit: int = 25) -> list[str]:
        """Return top seeds by fitness, discovery history, and recency."""
        records = self.data["records"]
        ranked = sorted(
            records.values(),
            key=lambda r: (
                r.get("discoveries", 0) * 2.0
                + r.get("fitness", 0)
                + (0.3 if r.get("last_used") else 0)
                + (0.5 if r.get("source") == "base" else 0)
            ),
            reverse=True,
        )
        seeds = [r["text"] for r in ranked[:limit]]
        for base in self.base_seeds:
            if base not in seeds:
                seeds.append(base)
        return seeds[:limit]

    def record_usage(self, seeds_used: list[str]) -> None:
        for text in seeds_used:
            rec = self.data["records"].get(_normalize(text))
            if rec:
                rec["uses"] = rec.get("uses", 0) + 1
                rec["last_used"] = _now_iso()

    def record_discovery(self, seeds_used: list[str], severity: float = 0.85) -> None:
        boost = 0.15 + severity * 0.25
        for text in seeds_used:
            rec = self.data["records"].get(_normalize(text))
            if rec:
                rec["discoveries"] = rec.get("discoveries", 0) + 1
                rec["fitness"] = min(5.0, rec.get("fitness", 1.0) + boost)

    def evolve_from_turn(
        self,
        turn: int,
        phase: str,
        expanded_terms: list[dict[str, Any]],
        correlation: dict[str, Any],
        findings: list[dict[str, Any]] | None = None,
        web_intel: list[dict[str, Any]] | None = None,
        adsb: dict[str, Any] | None = None,
    ) -> list[str]:
        """Generate seeds from a single analysis turn."""
        new_seeds: list[str] = []
        anchor = GEO_ANCHORS[turn % len(GEO_ANCHORS)]

        for term_obj in expanded_terms:
            score = term_obj.get("score", 0)
            term = term_obj.get("term", "")
            if score < 2.5 or not term:
                continue
            candidate = term_obj.get("suggested_query") or SEED_TEMPLATES[0].format(
                anchor=anchor, term=term
            )
            if self._upsert_record(
                self.data, candidate, source="term_boost", fitness=score / 2, tags=[term]
            ):
                new_seeds.append(candidate)

        for sig in correlation.get("signals", [])[:3]:
            candidate = SEED_TEMPLATES[1].format(anchor=anchor, signal=sig)
            if self._upsert_record(self.data, candidate, source="signal_reinforce", fitness=1.2, tags=[sig]):
                new_seeds.append(candidate)

        if adsb and adsb.get("aircraft_count", 0) > 3:
            low = adsb.get("low_altitude_under_8000ft", 0)
            candidate = f"{anchor} ADS-B surge {adsb['aircraft_count']} aircraft low-alt {low} military"
            if self._upsert_record(self.data, candidate, source="adsb_anomaly", fitness=1.5, tags=["adsb"]):
                new_seeds.append(candidate)

        if web_intel:
            for item in web_intel[-2:]:
                tags = item.get("tags", [])[:2]
                if len(tags) >= 2:
                    candidate = SEED_TEMPLATES[3].format(
                        anchor=anchor, tag1=tags[0], tag2=tags[1]
                    )
                    if self._upsert_record(self.data, candidate, source="web_intel", fitness=1.4, tags=tags):
                        new_seeds.append(candidate)

        for f in findings or []:
            if f.get("type") == "useful_discovery":
                title = f.get("id", "")
                if title:
                    candidate = f"Deep follow-up: {title[:120]}"
                    if self._upsert_record(self.data, candidate, source="useful_finding", fitness=2.0):
                        new_seeds.append(candidate)

        if new_seeds:
            self._log_evolution("turn", turn, phase, new_seeds)
        return new_seeds

    def evolve_from_cycle(self, cycle: int, context: dict[str, Any]) -> list[str]:
        """Synthesize composite seeds at end of a full phase rotation."""
        self.data["generation"] += 1
        self.data["evolution_cycles"] += 1
        new_seeds: list[str] = []

        top_terms = context.get("top_boosted_terms", [])[:3]
        top_sigs = list(context.get("reinforced_signals", {}).keys())[:2]
        anchor = GEO_ANCHORS[cycle % len(GEO_ANCHORS)]

        if top_terms:
            terms = ", ".join(t for t, _ in top_terms)
            candidate = SEED_TEMPLATES[4].format(terms=terms, anchor=anchor)
            if self._upsert_record(self.data, candidate, source="cycle_synthesis", fitness=2.2, tags=[t for t, _ in top_terms]):
                new_seeds.append(candidate)

        if top_terms and top_sigs:
            term = top_terms[0][0]
            sig = top_sigs[0]
            candidate = f"{anchor} {term} x {sig} recursive cycle {cycle} cross-domain"
            if self._upsert_record(self.data, candidate, source="cycle_crosslink", fitness=2.5):
                new_seeds.append(candidate)

        # Mutate a high-fitness seed with a new geo anchor
        active = self.get_active_seeds(limit=5)
        if active:
            parent = active[cycle % len(active)]
            new_anchor = GEO_ANCHORS[(cycle + 1) % len(GEO_ANCHORS)]
            mutated = re.sub(
                r"^(Sedona|KSEZ|Yavapai County|Luke AFB|Prescott VOR|northern Arizona|Verde Valley|Secret Mountain Wilderness)\b",
                new_anchor,
                parent,
                count=1,
            )
            if mutated == parent:
                mutated = f"{new_anchor} {parent}"
            if self._upsert_record(self.data, mutated, source="mutation", fitness=1.8, parent=parent):
                new_seeds.append(mutated)

        self._prune_inplace(self.data, keep=self.max_active)
        self._log_evolution("cycle", cycle, "complete", new_seeds)
        self.save()
        return new_seeds

    def evolve_from_swarm_report(self, report: dict[str, Any]) -> list[str]:
        """Generate seeds from a Yavapai swarm activation report."""
        self.data["evolution_cycles"] += 1
        new_seeds: list[str] = []
        summary = report.get("summary", {})
        real = report.get("real_data_summary", {}) or {}

        for sid in summary.get("signals_with_real_data", []):
            try:
                from ..config import SIGNALS
                sig_def = SIGNALS.get(int(sid))
                name = sig_def.name if sig_def else f"signal-{sid}"
            except Exception:
                name = f"signal-{sid}"
            candidate = SEED_TEMPLATES[2].format(
                signal_id=sid, signal_name=name, anchor="Yavapai"
            )
            if self._upsert_record(self.data, candidate, source="swarm_live_signal", fitness=1.6, tags=[str(sid)]):
                new_seeds.append(candidate)

        for check in report.get("cross_checks_performed", []):
            signals = check.get("signals") or check.get("note", "")
            if signals:
                candidate = f"Yavapai swarm cross-check {check.get('check', 'rule')} signals {signals}"
                if self._upsert_record(self.data, candidate, source="swarm_coupling", fitness=1.7):
                    new_seeds.append(candidate)

        for coupled in report.get("coupled_anomalies", []):
            sigs = coupled.get("signals", [])
            hyp = coupled.get("hypothesis", "")[:80]
            if sigs:
                candidate = f"Coupled anomaly follow-up signals {sigs}: {hyp}"
                if self._upsert_record(self.data, candidate, source="swarm_coupled", fitness=2.8):
                    new_seeds.append(candidate)

        errors = real.get("errors", {})
        for sid, err in errors.items():
            if err and "key" in err.lower():
                candidate = f"Resolve ingestor blocker signal {sid} unlock Yavapai depth"
                if self._upsert_record(self.data, candidate, source="swarm_blocker", fitness=1.3):
                    new_seeds.append(candidate)

        # Always produce at least one timestamped evolution seed per activation
        ts_seed = (
            f"Yavapai activation {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M')} "
            f"depth expansion signals {summary.get('signals_with_real_data', 'synthetic')}"
        )
        if self._upsert_record(self.data, ts_seed, source="activation_pulse", fitness=1.5):
            new_seeds.append(ts_seed)

        self._prune_inplace(self.data, keep=self.max_active)
        self._log_evolution("swarm_activation", 0, report.get("mode", ""), new_seeds)
        self.save()
        return new_seeds

    def get_priority_signal_ids(self) -> list[int]:
        """Infer which swarm signals to prioritize from evolved seed tags."""
        ids: list[int] = []
        for rec in self.data["records"].values():
            for tag in rec.get("tags", []):
                if tag.isdigit():
                    ids.append(int(tag))
            for m in re.findall(r"signal[_ ]?(\d+)", rec["text"], re.I):
                ids.append(int(m))
        # Default priority if none evolved yet
        if not ids:
            return [1, 4, 5, 7]
        seen: set[int] = set()
        ordered: list[int] = []
        for sid in sorted(ids, key=lambda x: -ids.count(x)):
            if sid not in seen and 1 <= sid <= 13:
                seen.add(sid)
                ordered.append(sid)
        return ordered[:8]

    def get_context(self) -> dict[str, Any]:
        active = self.get_active_seeds(limit=10)
        return {
            "registry_id": self.registry_id,
            "generation": self.data.get("generation", 0),
            "evolution_cycles": self.data.get("evolution_cycles", 0),
            "active_seed_count": len(self.data.get("records", {})),
            "active_seeds": active,
            "recent_evolutions": self.data.get("evolution_log", [])[-5:],
            "top_fitness": sorted(
                self.data.get("records", {}).values(),
                key=lambda r: r.get("fitness", 0),
                reverse=True,
            )[:5],
        }

    def _log_evolution(self, kind: str, cycle: int, phase: str, new_seeds: list[str]) -> None:
        self.data.setdefault("evolution_log", []).append({
            "kind": kind,
            "cycle": cycle,
            "phase": phase,
            "new_seeds": new_seeds[:8],
            "count": len(new_seeds),
            "ts": _now_iso(),
        })
        self.data["evolution_log"] = self.data["evolution_log"][-30:]