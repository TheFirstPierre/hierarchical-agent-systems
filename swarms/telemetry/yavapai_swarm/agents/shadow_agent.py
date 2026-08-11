"""
SHADOW Agent — overlay analyst for regional multi-domain anomaly anomaly missions.

Runs multi-turn analysis until a substantial discovery is made or the token
budget approaches its stop threshold (reserving tokens for the briefing PDF).
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .regional_targets import (
    ADS_B_BASELINE_AIRCRAFT,
    DEFAULT_SEEDS,
    DISCOVERY_THRESHOLDS,
    KSEZ_BBOX,
    DEFAULT_MISSION_ID,
)
from .shadow_intel import (
    MEMORY_PRIORITY_TERMS,
    USEFUL_CATEGORIES,
    WEB_INTEL_SOURCES,
    extract_snippets,
    score_memory_entry,
    synthesize_adaptive_finding,
    synthesize_triple_stack,
)
from .recursive_learning import RecursiveLearningStore
from .token_budget import TokenBudget, unlimited_tokens, unlimited_turns

# Prescott VOR bbox (ECHO signal 01 overlap region)
PRC_BBOX = {"lamin": 34.35, "lomin": -112.95, "lamax": 34.95, "lomax": -111.85}

DEEP_MODE_TOKEN_THRESHOLD = 20_000
MIN_USEFUL_SEVERITY = 0.85
MIN_TURNS_BEFORE_EARLY_STOP = 10  # require 2 full phase cycles before early exit
WEB_SOURCES_PER_TURN = 2

TURN_PHASES = [
    "memory_archaeology",
    "web_intel",
    "dual_adsb",
    "keyword_expansion",
    "intel_synthesis",
]

# Optional SESP integration (sibling package)
SESP_ROOT = Path(__file__).resolve().parents[3] / "swarm_evolving_protocol"
if SESP_ROOT.exists() and str(SESP_ROOT) not in sys.path:
    sys.path.insert(0, str(SESP_ROOT))


@dataclass
class ShadowDiscovery:
    discovery_id: str
    turn: int
    severity: float
    category: str
    title: str
    hypothesis: str
    evidence: dict[str, Any]
    correlated_terms: list[str] = field(default_factory=list)


@dataclass
class ShadowTurnRecord:
    turn: int
    action: str
    timestamp: str
    tokens_charged: int
    findings: list[dict[str, Any]] = field(default_factory=list)
    discovery_made: bool = False


@dataclass
class ShadowMissionResult:
    mission_id: str
    agent: str = "SHADOW"
    activation: str = "TELEMETRY_SWARM_V5_SHADOW"
    started_at: str = ""
    completed_at: str = ""
    stop_reason: str = ""
    turns_executed: int = 0
    discoveries: list[ShadowDiscovery] = field(default_factory=list)
    turn_log: list[ShadowTurnRecord] = field(default_factory=list)
    token_budget: dict[str, Any] = field(default_factory=dict)
    sedona_adsb: dict[str, Any] | None = None
    expanded_terms: list[dict[str, Any]] = field(default_factory=list)
    memory_hits: list[dict[str, Any]] = field(default_factory=list)
    coupled_anomalies: list[dict[str, Any]] = field(default_factory=list)
    useful_findings: list[dict[str, Any]] = field(default_factory=list)
    web_intel: list[dict[str, Any]] = field(default_factory=list)
    recursive_learning: dict[str, Any] = field(default_factory=dict)
    cycles_completed: int = 0
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "agent": self.agent,
            "activation": self.activation,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "stop_reason": self.stop_reason,
            "turns_executed": self.turns_executed,
            "discoveries": [d.__dict__ for d in self.discoveries],
            "turn_log": [t.__dict__ for t in self.turn_log],
            "token_budget": self.token_budget,
            "sedona_adsb": self.sedona_adsb,
            "expanded_terms": self.expanded_terms,
            "memory_hits": self.memory_hits,
            "coupled_anomalies": self.coupled_anomalies,
            "useful_findings": self.useful_findings,
            "web_intel": self.web_intel,
            "recursive_learning": self.recursive_learning,
            "cycles_completed": self.cycles_completed,
            "summary": self.summary,
        }


class ShadowAgent:
    """
    SHADOW overlay agent: regional multi-domain anomaly anomaly analysis.

    Turn sequence:
      1. SESP keyword expansion on mission seeds
      2. Live KSEZ ADS-B snapshot (OpenSky)
      3. SESP hierarchical memory retrieval
      4. Cross-correlation / anomaly scoring
      5. Repeat with rotated seed focus until discovery or token stop
    """

    def __init__(
        self,
        mission_id: str = DEFAULT_MISSION_ID,
        max_tokens: int = 0,
        stop_ratio: float = 0.00,
        seeds: list[str] | None = None,
        max_turns: int = 0,
        deep_mode: bool | None = None,
        recursive_loop: bool = False,
        duration_minutes: float | None = None,
        continue_after_discovery: bool = True,
    ):
        self.mission_id = mission_id
        self.seeds = seeds or DEFAULT_SEEDS
        self.deep_mode = deep_mode if deep_mode is not None else (
            unlimited_tokens(max_tokens) or max_tokens >= DEEP_MODE_TOKEN_THRESHOLD
        )
        self.recursive_loop = recursive_loop
        self.duration_minutes = duration_minutes
        self.continue_after_discovery = continue_after_discovery
        self.max_turns = max_turns  # 0 = unlimited
        self.budget = TokenBudget(max_tokens=max_tokens, stop_ratio=stop_ratio)
        self._learning = RecursiveLearningStore(mission_id)
        self.seeds = self._learning.get_enriched_seeds(self.seeds)
        self._turn = 0
        self._cycle = 0
        self._start_mono: float | None = None
        self._deadline_mono: float | None = None
        self._top_correlation = 0.0
        self._discoveries: list[ShadowDiscovery] = []
        self._useful_findings: list[dict[str, Any]] = []
        self._turn_log: list[ShadowTurnRecord] = []
        self._expanded_terms: list[dict[str, Any]] = []
        self._memory_hits: list[dict[str, Any]] = []
        self._web_intel: list[dict[str, Any]] = []
        self._sedona_adsb: dict[str, Any] | None = None
        self._prescott_adsb: dict[str, Any] | None = None
        self._coupled: list[dict[str, Any]] = []
        self._fetched_urls: set[str] = set()
        self._known_finding_keys: set[str] = self._learning.get_known_finding_keys()

    def _should_stop_on_useful(self) -> bool:
        """Only allow early stop in shallow quick mode after minimum production floor."""
        if self._turn < MIN_TURNS_BEFORE_EARLY_STOP:
            return False
        if self.continue_after_discovery and (self.deep_mode or self.recursive_loop):
            return False
        return True

    def run(self) -> ShadowMissionResult:
        started = datetime.now(timezone.utc)
        self._start_mono = time.monotonic()
        if self.duration_minutes:
            self._deadline_mono = self._start_mono + (self.duration_minutes * 60)
        stop_reason = "duration_limit_reached" if self.duration_minutes else "mission_open_ended"

        while (
            (unlimited_turns(self.max_turns) or self._turn < self.max_turns)
            and self.budget.can_continue
            and not self._time_expired()
        ):
            self._turn += 1
            useful, weak = self._execute_turn()

            if self._turn % len(TURN_PHASES) == 0:
                self._cycle += 1
                cycle_summary = self._learning.complete_cycle(
                    self._cycle,
                    len(self._useful_findings),
                    self._top_correlation,
                )
                self.seeds = self._learning.get_enriched_seeds(list(DEFAULT_SEEDS))
                self._fetched_urls.clear()
                if self.deep_mode or self.recursive_loop:
                    insight = self._learning.synthesize_cycle_insight(self._cycle)
                    if insight and insight.get("severity", 0) >= 0.80:
                        insight["discovery_id"] = f"SHADOW-RECURSE-{self.mission_id}-C{self._cycle:03d}"
                        key = insight.get("finding_key") or insight.get("title", "")
                        if key not in self._known_finding_keys:
                            insight["finding_key"] = f"cycle_insight_{self._cycle}"
                            self._useful_findings.append(insight)
                            self._known_finding_keys.add(insight["finding_key"])
                            self._learning.record_finding_key(insight["finding_key"])
                if self.recursive_loop:
                    time.sleep(2)

            if useful and self._should_stop_on_useful():
                stop_reason = "substantial_useful_discovery"
                break
            if weak and not self.deep_mode and not self.recursive_loop:
                stop_reason = "substantial_discovery"
                break
        else:
            if self._time_expired():
                stop_reason = "duration_limit_reached"
            elif not unlimited_turns(self.max_turns) and self._turn >= self.max_turns:
                stop_reason = "max_turns_reached"
            elif not self.budget.can_continue:
                stop_reason = "token_limit_approaching"
            if (self.deep_mode or self.recursive_loop) and not self._useful_findings:
                synth = self._final_synthesis()
                if synth:
                    self._useful_findings.append(synth)
                    stop_reason = "token_limit_with_synthesis"

        self._learning.save()
        completed = datetime.now(timezone.utc)
        elapsed_min = (time.monotonic() - self._start_mono) / 60 if self._start_mono else 0
        result = ShadowMissionResult(
            mission_id=self.mission_id,
            started_at=started.isoformat(),
            completed_at=completed.isoformat(),
            stop_reason=stop_reason,
            turns_executed=self._turn,
            discoveries=self._discoveries,
            turn_log=self._turn_log,
            token_budget=self.budget.summary(),
            sedona_adsb=self._sedona_adsb,
            expanded_terms=self._expanded_terms,
            memory_hits=self._memory_hits,
            coupled_anomalies=self._coupled,
            useful_findings=self._useful_findings,
            web_intel=self._web_intel,
            recursive_learning=self._learning.get_learning_context(),
            cycles_completed=self._cycle,
            summary=self._build_summary(stop_reason, elapsed_min),
        )
        return result

    def _time_expired(self) -> bool:
        if self._deadline_mono is None:
            return False
        return time.monotonic() >= self._deadline_mono

    def _execute_turn(self) -> tuple[bool, bool]:
        """Run one analysis turn. Returns (useful_discovery, weak_discovery)."""
        findings: list[dict[str, Any]] = []
        useful_made = False
        weak_made = False
        cost = 0

        phase = TURN_PHASES[(self._turn - 1) % len(TURN_PHASES)]
        seed_idx = (self._turn - 1) % len(self.seeds)
        active_seeds = [
            self.seeds[seed_idx % len(self.seeds)],
            self.seeds[(seed_idx + 1) % len(self.seeds)],
            "Sedona anomaly military correlation",
        ]
        if self._learning.data["learned_seeds"]:
            active_seeds.append(self._learning.data["learned_seeds"][-1])

        if phase == "memory_archaeology":
            memory = self._deep_memory_archaeology()
            cost += self.budget.charge(self._turn, "memory_archaeology", memory)
            self._memory_hits = memory
            findings.append({"type": "memory_archaeology", "count": len(memory), "top_score": memory[0].get("relevance_score", 0) if memory else 0})

        elif phase == "web_intel":
            web = self._fetch_web_intel()
            cost += self.budget.charge(self._turn, "web_intel", web)
            self._web_intel.extend(web)
            findings.append({"type": "web_intel", "fetched": len(web)})

        elif phase == "dual_adsb":
            adsb_ksez = self._fetch_sedona_adsb()
            adsb_prc = self._fetch_adsb_bbox(PRC_BBOX, "Prescott VOR")
            cost += self.budget.charge(self._turn, "dual_adsb", {"ksez": adsb_ksez, "prc": adsb_prc})
            self._sedona_adsb = adsb_ksez
            self._prescott_adsb = adsb_prc
            findings.append({"type": "dual_adsb", "ksez": adsb_ksez.get("aircraft_count"), "prc": adsb_prc.get("aircraft_count")})

        elif phase == "keyword_expansion":
            expansion = self._expand_keywords(active_seeds)
            cost += self.budget.charge(self._turn, "sesp_keyword_expansion", expansion)
            self._expanded_terms = expansion.get("expanded_terms", [])
            findings.append({"type": "keyword_expansion", "novel_count": expansion.get("total_novel", 0)})

        elif phase == "intel_synthesis":
            synth = self._intel_synthesis_turn(active_seeds)
            cost += self.budget.charge(self._turn, "intel_synthesis", synth)
            findings.append({"type": "intel_synthesis", "useful": synth.get("useful", False)})
            if synth.get("useful"):
                finding = synth["finding"]
                fkey = finding.get("finding_key") or finding.get("title", "")
                if fkey not in self._known_finding_keys:
                    self._useful_findings.append(finding)
                    self._known_finding_keys.add(fkey)
                    self._learning.record_finding_key(fkey)
                    useful_made = True
                    findings.append({"type": "useful_discovery", "id": finding.get("title")})
                    self._learning._seed_engine.record_discovery(active_seeds, severity=finding.get("severity", 0.9))
                else:
                    findings.append({"type": "duplicate_suppressed", "id": fkey})

        # Always correlate at end of turn if we have data
        adsb = self._sedona_adsb or {"aircraft_count": 0}
        memory = self._memory_hits or []
        expansion = {"expanded_terms": self._expanded_terms, "total_novel": 0}
        correlation = self._correlate(expansion, adsb, memory)
        cost += self.budget.charge(self._turn, "cross_correlation", correlation)
        findings.append({"type": "correlation", "score": correlation.get("score", 0)})
        self._top_correlation = max(self._top_correlation, correlation.get("score", 0))

        learn_delta = self._learning.absorb_turn(
            self._turn, phase, findings,
            self._expanded_terms, correlation,
            self._sedona_adsb, self._prescott_adsb,
            web_intel=self._web_intel[-5:] if self._web_intel else None,
            active_seeds=active_seeds,
        )
        if learn_delta.get("new_seeds"):
            self.seeds = self._learning.get_enriched_seeds(list(DEFAULT_SEEDS))
        if learn_delta.get("new_seeds") or learn_delta.get("boosted"):
            findings.append({"type": "recursive_learning", "delta": learn_delta})

        if not useful_made:
            discovery = self._evaluate_discovery(expansion, adsb, memory, correlation)
            if discovery:
                self._discoveries.append(discovery)
                weak_made = True
                findings.append({"type": "weak_discovery", "id": discovery.discovery_id})

        self._turn_log.append(ShadowTurnRecord(
            turn=self._turn,
            action=f"sedona_shadow_{phase}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            tokens_charged=cost,
            findings=findings,
            discovery_made=useful_made or weak_made,
        ))
        return useful_made, weak_made

    def _expand_keywords(self, seeds: list[str]) -> dict[str, Any]:
        try:
            from modules.discovery.keyword_expander import expand_keywords
            return expand_keywords(seeds, max_novel_terms=12, mission_id=self.mission_id)
        except ImportError:
            return self._fallback_expansion(seeds)

    def _fallback_expansion(self, seeds: list[str]) -> dict[str, Any]:
        terms = [
            {"term": "military", "score": 4.0, "reason": "high co-occurrence with seeds + low prior memory presence", "suggested_query": f"{seeds[0]} military"},
            {"term": "arizona", "score": 4.0, "reason": "high co-occurrence with seeds + low prior memory presence", "suggested_query": f"{seeds[0]} arizona"},
            {"term": "black", "score": 2.0, "reason": "strong correlation with existing swarm knowledge", "suggested_query": f"{seeds[0]} black hawk"},
            {"term": "yavapai", "score": 2.0, "reason": "strong correlation with existing swarm knowledge", "suggested_query": f"{seeds[0]} yavapai"},
        ]
        return {
            "mission_id": self.mission_id,
            "original_seeds": seeds,
            "expanded_terms": terms,
            "total_novel": 2,
            "protocol_version": "SHADOW-FALLBACK",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _fetch_adsb_bbox(self, bbox: dict[str, float], label: str) -> dict[str, Any]:
        url = "https://opensky-network.org/api/states/all"
        params = {"lamin": bbox["lamin"], "lomin": bbox["lomin"], "lamax": bbox["lamax"], "lomax": bbox["lomax"]}
        try:
            with httpx.Client(timeout=12.0, headers={"User-Agent": "yavapai-swarm-shadow/5.0"}) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 429:
                    return {"error": "rate_limited", "aircraft_count": 0, "bbox": bbox, "label": label}
                resp.raise_for_status()
                states = resp.json().get("states") or []
        except Exception as exc:
            return {"error": str(exc), "aircraft_count": 0, "bbox": bbox, "label": label}

        low_alt = sum(1 for s in states if (s[7] or s[13]) is not None and (s[7] or s[13]) < 8000)
        mil_suspect = sum(1 for s in states if (s[1] or "").strip() and not (s[1] or "").strip().startswith("N"))
        return {
            "aircraft_count": len(states),
            "low_altitude_under_8000ft": low_alt,
            "non_ga_callsigns": mil_suspect,
            "bbox": bbox,
            "label": label,
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": f"OpenSky Network ({label})",
        }

    def _fetch_sedona_adsb(self) -> dict[str, Any]:
        result = self._fetch_adsb_bbox(KSEZ_BBOX, "KSEZ Sedona")
        result["elevated_vs_baseline"] = result.get("aircraft_count", 0) > ADS_B_BASELINE_AIRCRAFT
        result["baseline"] = ADS_B_BASELINE_AIRCRAFT
        return result

    def _deep_memory_archaeology(self) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        warm = SESP_ROOT / "memory" / "warm_archive.jsonl"
        if warm.exists():
            for line in warm.read_text().splitlines():
                try:
                    entry = json.loads(line)
                    summary = entry.get("summary") or ""
                    meta = entry.get("metadata") or {}
                    text = summary.lower()
                    priority = set(MEMORY_PRIORITY_TERMS) | set(self._learning.data["boosted_terms"].keys())
                    if not any(t in text for t in priority):
                        continue
                    score = score_memory_entry(summary, meta)
                    for term, boost in self._learning.data["boosted_terms"].items():
                        if term in text:
                            score = min(1.0, score + boost * 0.05)
                    hits.append({
                        "source": "warm_archive",
                        "id": entry.get("id"),
                        "summary": summary[:400],
                        "mission": entry.get("mission"),
                        "metadata": meta,
                        "relevance_score": round(score, 2),
                        "url": meta.get("url"),
                    })
                except json.JSONDecodeError:
                    continue
        hits.sort(key=lambda x: -x.get("relevance_score", 0))
        return hits[:15]

    def _fetch_web_intel(self) -> list[dict[str, Any]]:
        """Rotate and fetch fresh sources each turn; cache resets every cycle."""
        fetched: list[dict[str, Any]] = []
        sources = WEB_INTEL_SOURCES
        start = (self._turn - 1) % len(sources)
        ordered = sources[start:] + sources[:start]
        ts = int(time.time())
        for src in ordered:
            if len(fetched) >= WEB_SOURCES_PER_TURN:
                break
            cache_key = f"{src['id']}|c{self._cycle}|t{self._turn}"
            if cache_key in self._fetched_urls:
                continue
            url = src["url"]
            sep = "&" if "?" in url else "?"
            fetch_url = f"{url}{sep}_shadow={ts}"
            try:
                with httpx.Client(timeout=15.0, headers={"User-Agent": "yavapai-swarm-shadow/5.0"}, follow_redirects=True) as client:
                    resp = client.get(fetch_url)
                    resp.raise_for_status()
                    snippet = extract_snippets(resp.text, 1500)
            except Exception as exc:
                snippet = f"fetch_failed: {exc}"
            self._fetched_urls.add(cache_key)
            item = {
                "id": src["id"],
                "url": src["url"],
                "tags": src["tags"],
                "relevance": src["relevance"],
                "snippet": snippet,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "fetch_cycle": self._cycle,
                "fetch_turn": self._turn,
            }
            fetched.append(item)
            self._web_intel.append(item)
        return fetched

    def _intel_synthesis_turn(self, active_seeds: list[str]) -> dict[str, Any]:
        adsb = self._sedona_adsb or {"aircraft_count": 0, "low_altitude_under_8000ft": 0}
        novel = synthesize_adaptive_finding(
            cycle=self._cycle,
            turn=self._turn,
            active_seeds=active_seeds,
            web_items=self._web_intel,
            memory_items=self._memory_hits,
            adsb_ksez=adsb,
            adsb_prc=self._prescott_adsb,
            boosted_terms=self._learning.data["boosted_terms"],
            known_keys=self._known_finding_keys,
        )
        if novel and novel.get("severity", 0) >= MIN_USEFUL_SEVERITY:
            novel["discovery_id"] = f"SHADOW-NOVEL-{self.mission_id}-T{self._turn:03d}"
            return {"useful": True, "finding": novel, "source": "adaptive"}

        triple = synthesize_triple_stack(self._web_intel, self._memory_hits, adsb)
        if triple:
            tkey = triple.get("finding_key", triple.get("title", ""))
            if tkey not in self._known_finding_keys and triple.get("severity", 0) >= MIN_USEFUL_SEVERITY:
                triple["discovery_id"] = f"SHADOW-USEFUL-{self.mission_id}-T{self._turn:03d}"
                return {"useful": True, "finding": triple, "source": "triple_stack"}

        return {"useful": False, "signals_checked": triple.get("signals") if triple else [], "source": "none"}

    def _final_synthesis(self) -> dict[str, Any] | None:
        """Last-chance synthesis when approaching token limit."""
        if not self._web_intel and not self._memory_hits:
            return None
        triple = synthesize_triple_stack(self._web_intel, self._memory_hits, self._sedona_adsb or {})
        if triple:
            triple["discovery_id"] = f"SHADOW-SYNTH-{self.mission_id}-FINAL"
            triple["note"] = "Synthesized at token limit from accumulated intel"
            return triple
        return None

    def _query_memory(self, seeds: list[str]) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        try:
            from modules.memory.hierarchical_store import HierarchicalMemory
            mem = HierarchicalMemory(mission_id=self.mission_id)
            summary = mem.get_mission_summary()
            if summary:
                hits.append({"source": "mission_summary", "content": summary})
            # Also scan warm archive for Sedona/anomaly terms
            warm = SESP_ROOT / "memory" / "warm_archive.jsonl"
            if warm.exists():
                seed_words = set(" ".join(seeds).lower().split())
                for line in warm.read_text().splitlines()[-50:]:
                    try:
                        entry = json.loads(line)
                        text = (entry.get("summary") or "").lower()
                        if any(w in text for w in seed_words | {"sedona", "anomaly", "military", "black hawk", "ksez"}):
                            hits.append({
                                "source": "warm_archive",
                                "id": entry.get("id"),
                                "summary": entry.get("summary", "")[:300],
                                "mission": entry.get("mission"),
                            })
                    except json.JSONDecodeError:
                        continue
        except ImportError:
            hits.append({
                "source": "fallback",
                "summary": "SESP memory unavailable; using embedded Sedona baseline knowledge.",
            })
        return hits[:8]

    def _correlate(
        self,
        expansion: dict[str, Any],
        adsb: dict[str, Any],
        memory: list[dict[str, Any]],
    ) -> dict[str, Any]:
        terms = expansion.get("expanded_terms", [])
        top_terms = [t["term"] for t in terms[:5] if t.get("score", 0) >= 2.0]
        mil_terms = [t for t in top_terms if t in {"military", "black", "hawk", "luke", "mtr", "moa", "anomaly"}]

        score = 0.0
        signals: list[str] = []

        if adsb.get("elevated_vs_baseline"):
            score += 0.25
            signals.append("adsb_elevated")
        if adsb.get("low_altitude_under_8000ft", 0) >= 2:
            score += 0.20
            signals.append("low_alt_training_pattern")
        if mil_terms:
            score += 0.15 * min(len(mil_terms), 3)
            signals.append("military_term_correlation")
        if memory:
            score += 0.10
            signals.append("memory_corroboration")
        if expansion.get("total_novel", 0) >= 2:
            score += 0.15
            signals.append("novel_discovery_terms")

        score = min(1.0, score)
        coupled = None
        if score >= DISCOVERY_THRESHOLDS["correlation_score"] and adsb.get("elevated_vs_baseline"):
            coupled = {
                "coupling_id": f"SHADOW-CPL-{self._turn:03d}",
                "clusters": ["ECHO", "SHADOW"],
                "signals": [1, "SEDONA_ADSB"],
                "severity": round(score, 2),
                "hypothesis": (
                    "Elevated KSEZ-area ADS-B traffic temporally correlates with "
                    "military/anomaly expansion terms from SESP discovery layer."
                ),
                "terms": top_terms,
            }
            self._coupled.append(coupled)

        return {
            "score": round(score, 3),
            "signals": signals,
            "top_terms": top_terms,
            "coupled_anomaly": coupled,
        }

    def _evaluate_discovery(
        self,
        expansion: dict[str, Any],
        adsb: dict[str, Any],
        memory: list[dict[str, Any]],
        correlation: dict[str, Any],
    ) -> ShadowDiscovery | None:
        terms = expansion.get("expanded_terms", [])
        max_score = max((t.get("score", 0) for t in terms), default=0)
        high_terms = [t for t in terms if t.get("score", 0) >= 3.0]

        reasons: list[str] = []
        severity = 0.0

        if max_score >= DISCOVERY_THRESHOLDS["novel_term_score"]:
            reasons.append(f"Novel term score {max_score} exceeds threshold")
            severity = max(severity, 0.75)
        if len(high_terms) >= DISCOVERY_THRESHOLDS["novel_term_count_at_3"]:
            reasons.append(f"{len(high_terms)} terms scored >= 3.0")
            severity = max(severity, 0.70)
        if correlation.get("score", 0) >= DISCOVERY_THRESHOLDS["correlation_score"]:
            reasons.append(f"Cross-correlation score {correlation['score']}")
            severity = max(severity, correlation["score"])
        if adsb.get("aircraft_count", 0) >= DISCOVERY_THRESHOLDS["adsb_elevated_count"]:
            reasons.append(f"ADS-B count {adsb['aircraft_count']} exceeds elevated threshold")
            severity = max(severity, 0.80)

        if not reasons:
            return None

        top = terms[0] if terms else {"term": "unknown", "score": 0}
        return ShadowDiscovery(
            discovery_id=f"SHADOW-DISC-{self.mission_id}-{self._turn:03d}",
            turn=self._turn,
            severity=round(min(1.0, severity), 2),
            category="regional_anomaly_monitor",
            title=f"Substantial discovery: {top.get('term', 'correlation')} (turn {self._turn})",
            hypothesis="; ".join(reasons),
            evidence={
                "top_term": top,
                "high_terms": high_terms[:5],
                "adsb": adsb,
                "correlation": correlation,
                "memory_hit_count": len(memory),
            },
            correlated_terms=[t["term"] for t in terms[:8]],
        )

    def _build_summary(self, stop_reason: str, elapsed_min: float = 0) -> dict[str, Any]:
        useful_sev = max((f.get("severity", 0) for f in self._useful_findings), default=0)
        top_useful = max(self._useful_findings, key=lambda f: f.get("severity", 0), default=None) if self._useful_findings else None
        return {
            "mission": "Regional multi-domain anomaly Anomaly Analysis",
            "deep_mode": self.deep_mode,
            "recursive_loop": self.recursive_loop,
            "duration_minutes_requested": self.duration_minutes,
            "elapsed_minutes": round(elapsed_min, 2),
            "cycles_completed": self._cycle,
            "max_turns": self.max_turns,
            "max_tokens": self.budget.max_tokens,
            "stop_ratio": self.budget.stop_ratio,
            "stop_reason": stop_reason,
            "substantial_discoveries": len(self._discoveries),
            "useful_findings": len(self._useful_findings),
            "coupled_anomalies": len(self._coupled),
            "web_intel_items": len(self._web_intel),
            "memory_hits": len(self._memory_hits),
            "tokens_remaining_for_briefing": self.budget.remaining,
            "highest_severity": max(useful_sev, max((d.severity for d in self._discoveries), default=0)),
            "top_useful_title": top_useful.get("title") if top_useful else None,
            "actionable_insights": top_useful.get("actionable_insights", []) if top_useful else [],
            "recursive_learning": self._learning.get_learning_context() if self.recursive_loop else {},
            "recommendation": (
                top_useful.get("hypothesis", "")[:300] if top_useful else
                "Continue deep SHADOW passes with live OSINT and EIA grid key for cross-domain checks."
            ),
        }