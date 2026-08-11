#!/usr/bin/env python3
"""
SESP Novel Data Discovery Module: Keyword Cross-Correlation Expander
Version: 1.0 (2026-05-28)

Purpose: Takes seed keywords (e.g. from ALPHA or CHARLIE queries) and generates
novel, high-value expansion terms by identifying cross-correlations from search
results, prior swarm memory, and simple co-occurrence analysis.

This is the first self-evolving component. Agents can propose improved heuristics
via the proposal schema.

Usage (example for regional military deep dive):
    from modules.discovery.keyword_expander import expand_keywords
    seeds = ["regional Arizona military", "KSEZ Black Hawk"]
    expansions = expand_keywords(seeds, max_novel_terms=15)
    print(expansions)
"""

import json
import re
import hashlib
from datetime import datetime
from pathlib import Path
from collections import Counter
from typing import List, Dict, Set

# --- Configuration (self-evolvable via proposals) ---
BASE_DIR = Path(__file__).parent.parent.parent
MEMORY_INDEX = BASE_DIR / "memory" / "swarm_memory_index.jsonl"
PROPOSALS_DIR = BASE_DIR / "proposals"
LOG_FILE = BASE_DIR / "logs" / "discovery_log.jsonl"

# Simple stopword list (expandable)
STOPWORDS = {"the", "and", "for", "with", "that", "this", "from", "have", "been", "was", "were", "are", "is", "of", "in", "to", "a", "an", "on", "by", "at", "as", "it", "be", "or", "not"}

def _log_event(event: dict):
    """Append-only audit log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    event["timestamp"] = datetime.utcnow().isoformat()
    event["hash"] = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()[:16]
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

def _load_prior_memory() -> Set[str]:
    """Load historical terms from swarm memory for correlation (token-efficient)."""
    terms = set()
    if MEMORY_INDEX.exists():
        with open(MEMORY_INDEX) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if "keywords" in data:
                        terms.update(data["keywords"])
                except:
                    continue
    return terms

def _simple_cooccurrence_expansion(seeds: List[str], prior_terms: Set[str], top_n: int = 20) -> List[Dict]:
    """
    Core novel discovery logic (v1.0 baseline).
    In real deployment, this would call web_search or internal index.
    Here we simulate + use prior memory for cross-correlation.
    """
    # Simulated "search" results (in practice: call web_search tool with seeds)
    # For demo, we hardcode plausible regional/AZ military correlations + allow dynamic extension.
    simulated_results = [
        "Luke AFB F-35 low level training routes northern Arizona MTR IR-112",
        "Yavapai County military operations areas Bagdad Gladden MOA",
        "regional Airport KSEZ UH-60 Black Hawk May 2026 operations",
        "AFSOC U-28A Draco visits to civilian airports Arizona",
        "Coconino National Forest Bradshaw Ranch USFS acquisition 2001",
        "Secret Mountain Wilderness military overflights vortex area",
        "Arizona National Guard Black Hawk SAR Yavapai County 2026",
        "PURSUE UAP Release 02 CENTCOM orbs military sensor data",
        "regional red rocks low flying military helicopters resident reports",
        "Luke Air Force Base MACA pamphlets northern Arizona",
    ]

    # Add prior swarm memory for real cross-correlation
    simulated_results.extend(list(prior_terms)[:30])

    all_text = " ".join(simulated_results + seeds).lower()
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9\-]{2,}\b', all_text)
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]

    # Cross-correlation: terms that appear with multiple seeds
    seed_set = set(" ".join(seeds).lower().split())
    cooccurring = Counter()
    for word in filtered:
        if any(seed in word or word in seed for seed in seed_set):
            cooccurring[word] += 2  # boost direct correlations
        else:
            cooccurring[word] += 1

    # Novelty scoring (self-evolving metric)
    novel_terms = []
    for term, freq in cooccurring.most_common(top_n * 2):
        if term in seed_set or len(term) < 4:
            continue
        novelty_score = freq * (1.0 if term not in prior_terms else 0.3)
        if novelty_score > 1.5:
            novel_terms.append({
                "term": term,
                "score": round(novelty_score, 2),
                "reason": "high co-occurrence with seeds + low prior memory presence" if term not in prior_terms else "strong correlation with existing swarm knowledge",
                "suggested_query": f"{seeds[0]} {term}"
            })

    return sorted(novel_terms, key=lambda x: -x["score"])[:top_n]

def expand_keywords(seed_keywords: List[str], max_novel_terms: int = 12, mission_id: str = "default") -> Dict:
    """
    Main public API for agents (ALPHA, CHARLIE, etc.).
    Returns expanded terms + metadata for logging/proposals.
    """
    prior = _load_prior_memory()
    expansions = _simple_cooccurrence_expansion(seed_keywords, prior, max_novel_terms)

    result = {
        "mission_id": mission_id,
        "original_seeds": seed_keywords,
        "expanded_terms": expansions,
        "total_novel": len([e for e in expansions if "low prior" in e["reason"]]),
        "protocol_version": "SESP-1.0",
        "timestamp": datetime.utcnow().isoformat()
    }

    _log_event({
        "type": "discovery_expansion",
        "seeds": seed_keywords,
        "novel_count": result["total_novel"],
        "mission": mission_id
    })

    return result

# --- Self-Evolution Hook (agents can call this to propose improvements) ---
def propose_new_heuristic(description: str, new_code_snippet: str, expected_gain: str):
    """Helper for agents to generate a valid proposal."""
    proposal = {
        "proposal_id": f"SESP-DISC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        "proposing_agent": "ALPHA or CHARLIE",
        "change_type": "KEYWORD_EXPANDER_HEURISTIC",
        "rationale": description,
        "expected_impact": {"novel_data_gain": expected_gain},
        "patch_or_code": new_code_snippet,
        "tests": ["Run on regional military seeds and measure new relevant terms discovered"],
        "risk_assessment": {
            "data_leakage_risk": "LOW",
            "user_privacy_impact": "None - operates on public search terms only",
            "reversibility": True
        },
        "rationale": "Increases ability to surface hidden correlations in military/UAP/OSINT deep dives (e.g. regional, future targets)."
    }
    return proposal

if __name__ == "__main__":
    # Demo for regional military activity
    demo_seeds = ["regional Arizona military activity", "KSEZ Black Hawk overflight", "regional UAP military"]
    output = expand_keywords(demo_seeds, mission_id="sedona-2026-05-28")
    print(json.dumps(output, indent=2))