"""
Curated intel sources and synthesis helpers for SHADOW deep missions.
"""
from __future__ import annotations

import re
from typing import Any

# Public sources SHADOW may fetch (always-ask respected at CLI layer)
WEB_INTEL_SOURCES = [
    {
        "id": "pursue_overview",
        "url": "https://defensescoop.com/2026/05/14/anomaly-trump-first-pursue-ufo-file-drop/",
        "tags": ["anomaly", "pursue", "military", "declassification"],
        "relevance": 0.95,
    },
    {
        "id": "az_ufo_archive",
        "url": "https://www.aol.com/articles/more-arizona-ufo-sightings-revealed-120312000.html",
        "tags": ["arizona", "anomaly", "fbi", "sedona", "phoenix"],
        "relevance": 0.92,
    },
    {
        "id": "pentagon_ufo_release",
        "url": "https://www.azfamily.com/2026/05/08/pentagon-begins-releasing-new-files-ufos-says-public-can-draw-its-own-conclusions/",
        "tags": ["anomaly", "pentagon", "arizona", "military"],
        "relevance": 0.90,
    },
    {
        "id": "pocket_fire_sedona",
        "url": "https://www.azfamily.com/2026/06/22/pocket-fire-burns-over-250-acres-north-sedona-sparks-evacuations/",
        "tags": ["sedona", "fire", "aviation", "sar", "emergency"],
        "relevance": 0.98,
    },
    {
        "id": "burlison_mitre",
        "url": "https://defensescoop.com/2026/05/27/rep-eric-burlison-request-for-anomaly-records-mitre/",
        "tags": ["anomaly", "mitre", "burlison", "military", "sensor"],
        "relevance": 0.94,
    },
]

MEMORY_PRIORITY_TERMS = {
    "black hawk", "ksez", "sedona", "anomaly", "mitre", "burlison", "pursue",
    "military", "mtr", "moa", "luke", "yavapai", "sensor", "war.gov",
}

USEFUL_CATEGORIES = {
    "OPERATIONAL_CROSS_LINK",
    "anomaly_DECLASS_PIPELINE",
    "SEDONA_LIVE_CONTEXT",
    "MILITARY_AVIATION_CORRIDOR",
    "MEMORY_WEB_CORROBORATION",
}


def extract_snippets(html: str, max_len: int = 1200) -> str:
    """Strip tags and return readable text snippet."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def score_memory_entry(summary: str, metadata: dict[str, Any]) -> float:
    text = (summary or "").lower()
    score = 0.0
    for term in MEMORY_PRIORITY_TERMS:
        if term in text:
            score += 0.12
    if metadata.get("action") == "real_fetch":
        score += 0.15
    if metadata.get("type") in ("named_intelligence_target", "discovery_surface_attempt"):
        score += 0.10
    if "burlison" in text or "mitre" in text:
        score += 0.25
    if "black hawk" in text or "ksez" in text:
        score += 0.30
    return min(1.0, score)


def synthesize_triple_stack(
    web_items: list[dict[str, Any]],
    memory_items: list[dict[str, Any]],
    adsb: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Build the highest-value cross-link: Sedona operational + anomaly pipeline + military aviation.
    Returns useful intel dict or None.
    """
    has_fire = any(
        w.get("id") == "pocket_fire_sedona"
        or "pocket fire" in (w.get("snippet") or "").lower()
        for w in web_items
    )
    has_pursue = any(
        w.get("id") == "pursue_overview"
        or "pursue" in (w.get("snippet") or "").lower()
        for w in web_items
    )
    has_az_anomaly = any(
        w.get("id") == "az_ufo_archive"
        or ("arizona" in (w.get("snippet") or "").lower() and "ufo" in (w.get("snippet") or "").lower())
        for w in web_items
    )
    has_burlison_mem = any(
        "burlison" in (m.get("summary") or "").lower() or "mitre" in (m.get("summary") or "").lower()
        for m in memory_items
    )
    has_ksez_mem = any(
        "ksez" in (m.get("summary") or "").lower() or "black hawk" in (m.get("summary") or "").lower()
        for m in memory_items
    )

    signals = []
    if has_fire:
        signals.append("sedona_pocket_fire_jun2026")
    if has_pursue:
        signals.append("pursue_anomaly_release_may2026")
    if has_az_anomaly:
        signals.append("arizona_fbi_anomaly_archive")
    if has_burlison_mem:
        signals.append("burlison_mitre_interrogatories")
    if has_ksez_mem:
        signals.append("ksez_blackhawk_may2026_memory")
    if adsb.get("low_altitude_under_8000ft", 0) > 0:
        signals.append("live_low_alt_adsb_ksez")

    if len(signals) < 3:
        return None

    severity = min(0.98, 0.70 + 0.05 * len(signals))

    return {
        "category": "OPERATIONAL_CROSS_LINK",
        "severity": round(severity, 2),
        "title": "Sedona Triple-Stack Anomaly Window (Fire + anomaly Pipeline + Military Aviation)",
        "finding_key": "triple_stack_baseline",
        "hypothesis": (
            "SHADOW cross-linked live Sedona operational context (Pocket Fire north of Sedona, "
            "Jun 2026 evacuations/SAR aviation) with the active federal anomaly declassification pipeline "
            "(PURSUE release, war.gov/ufo, 160+ files May 2026) and SESP memory of KSEZ Black Hawk "
            "low-level operations (May 4 2026). Arizona-specific FBI anomaly archive confirms decades of "
            "federal investigation in this corridor. Burlison MITRE interrogatories (May 26) target "
            "contractor-held anomaly sensor data — directly relevant to military sensor correlation "
            "over northern Arizona training routes (MTR IR-112 / Luke AFB)."
        ),
        "actionable_insights": [
            "Monitor KSEZ ADS-B during Pocket Fire SAR window for non-GA/military helicopter signatures",
            "Cross-reference PURSUE files at war.gov/ufo for Arizona/INDOPACOM entries near AZ borders",
            "Track Burlison MITRE response for released contractor anomaly sensor metadata",
            "Fire-induced APS power shutoffs (10K customers northern AZ Jun 24) may correlate with grid signal 04 when EIA key configured",
        ],
        "signals": signals,
        "evidence_sources": [w.get("id") for w in web_items[:5]] + [m.get("id", m.get("source", "")) for m in memory_items[:3]],
    }


def synthesize_adaptive_finding(
    cycle: int,
    turn: int,
    active_seeds: list[str],
    web_items: list[dict[str, Any]],
    memory_items: list[dict[str, Any]],
    adsb_ksez: dict[str, Any],
    adsb_prc: dict[str, Any] | None,
    boosted_terms: dict[str, float],
    known_keys: set[str],
) -> dict[str, Any] | None:
    """
    Produce a novel finding from live rotation context — never replay cached baselines.
    """
    seed_focus = active_seeds[turn % len(active_seeds)] if active_seeds else "Sedona military anomaly"
    top_terms = sorted(boosted_terms.items(), key=lambda x: -x[1])[:4]
    ksez_n = adsb_ksez.get("aircraft_count", 0)
    prc_n = (adsb_prc or {}).get("aircraft_count", 0)
    ksez_low = adsb_ksez.get("low_altitude_under_8000ft", 0)
    fresh_web = [w for w in web_items if w.get("fetched_at")][-3:]
    web_ids = [w.get("id", "") for w in fresh_web if w.get("id")]

    candidates: list[dict[str, Any]] = []

    if ksez_n != prc_n and (ksez_n > 0 or prc_n > 0):
        candidates.append({
            "finding_key": f"adsb_divergence_c{cycle}_t{turn}",
            "category": "MILITARY_AVIATION_CORRIDOR",
            "severity": min(0.96, 0.82 + 0.02 * abs(ksez_n - prc_n)),
            "title": f"Cycle {cycle} ADS-B Corridor Divergence — KSEZ {ksez_n} vs Prescott {prc_n}",
            "hypothesis": (
                f"Live dual-ADS-B snapshot (turn {turn}) shows asymmetric traffic: KSEZ={ksez_n} "
                f"(low-alt {ksez_low}) vs Prescott VOR={prc_n}. Seed focus '{seed_focus[:60]}' "
                "suggests training-route or SAR-corridor activity worth cross-checking against "
                "reinforced memory and federal anomaly pipeline releases."
            ),
            "actionable_insights": [
                f"Re-sample ADS-B next cycle; delta target > {max(1, abs(ksez_n - prc_n))}",
                "Correlate low-alt KSEZ tracks with Pocket Fire SAR window",
                f"Expand seed: {seed_focus[:80]}",
            ],
            "signals": ["live_ksez_adsb", "live_prc_adsb", f"cycle_{cycle}"],
            "evidence_sources": web_ids + [m.get("id", "") for m in memory_items[:2]],
        })

    if top_terms:
        term_str = ", ".join(t for t, _ in top_terms)
        candidates.append({
            "finding_key": f"boosted_terms_c{cycle}_t{turn}",
            "category": "MEMORY_WEB_CORROBORATION",
            "severity": min(0.94, 0.78 + 0.04 * len(top_terms)),
            "title": f"Cycle {cycle} Boosted-Term Correlation ({term_str[:50]})",
            "hypothesis": (
                f"Recursive learning reinforced {term_str} against seed '{seed_focus[:50]}'. "
                f"Web intel sources {web_ids or ['pending']} and {len(memory_items)} memory hits "
                f"support continued depth expansion on turn {turn}."
            ),
            "actionable_insights": [
                f"Prioritize evolved seed: {active_seeds[-1][:80]}" if len(active_seeds) > 1 else "Rotate seed focus",
                "Fetch unfetched web sources next web_intel phase",
                "Cross-check PURSUE war.gov/ufo for Arizona entries matching top terms",
            ],
            "signals": [t for t, _ in top_terms[:5]] + [f"cycle_{cycle}"],
            "evidence_sources": web_ids,
        })

    if fresh_web:
        tags: list[str] = []
        for w in fresh_web:
            tags.extend(w.get("tags", [])[:2])
        uniq_tags = list(dict.fromkeys(tags))[:4]
        if len(uniq_tags) >= 2:
            candidates.append({
                "finding_key": f"web_fresh_c{cycle}_t{turn}_{fresh_web[-1].get('id', 'x')}",
                "category": "SEDONA_LIVE_CONTEXT",
                "severity": 0.86,
                "title": f"Cycle {cycle} Fresh Intel Cross-Link ({uniq_tags[0]} + {uniq_tags[1]})",
                "hypothesis": (
                    f"Newly fetched source '{fresh_web[-1].get('id')}' tags {uniq_tags} "
                    f"intersect seed focus '{seed_focus[:50]}' and live KSEZ count {ksez_n}."
                ),
                "actionable_insights": [
                    f"Deep-read source: {fresh_web[-1].get('url', '')[:90]}",
                    "Synthesize with next memory_archaeology pass",
                ],
                "signals": uniq_tags + [f"cycle_{cycle}"],
                "evidence_sources": [w.get("id", "") for w in fresh_web],
            })

    for cand in sorted(candidates, key=lambda c: -c["severity"]):
        if cand["finding_key"] not in known_keys:
            cand["cycle"] = cycle
            cand["turn"] = turn
            cand["seed_focus"] = seed_focus
            return cand
    return None