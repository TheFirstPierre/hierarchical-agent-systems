#!/usr/bin/env python3
"""
SESP Novel Memory, Storage & Token Utilization Module
Version: 1.0 (2026-05-28)

Hierarchical memory with automatic summarization, deduplication, and token-aware retrieval.
Designed for long-running OSINT swarms (e.g. multi-day regional or multi-target campaigns).

Self-evolving: Agents propose better summarizers or retrieval strategies.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

BASE_DIR = Path(__file__).parent.parent.parent
MEMORY_DIR = BASE_DIR / "memory"
HOT_CACHE = MEMORY_DIR / "hot_cache.json"
WARM_ARCHIVE = MEMORY_DIR / "warm_archive.jsonl"
COLD_ARCHIVE = MEMORY_DIR / "cold_archive.jsonl"
INDEX_FILE = MEMORY_DIR / "retrieval_index.json"

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]

def _summarize(text: str, max_sentences: int = 4) -> str:
    """Lightweight extractive summarizer (v1.0 baseline - self-evolvable)."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= max_sentences:
        return text
    # Prefer sentences with numbers, proper nouns, or key OSINT terms
    scored = []
    keywords = {"military", "uap", "sedona", "black hawk", "ksez", "mtr", "moa", "notam", "helicopter", "overflight", "vortex", "bradshaw"}
    for s in sentences:
        score = sum(1 for k in keywords if k in s.lower()) + (2 if re.search(r'\d{4}|\d{2}:\d{2}', s) else 0)
        scored.append((score, s))
    scored.sort(reverse=True)
    return " ".join([s for _, s in scored[:max_sentences]])

class HierarchicalMemory:
    def __init__(self, mission_id: str = "default"):
        self.mission_id = mission_id
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.hot = self._load_hot()
        self.index = self._load_index()

    def _load_hot(self) -> Dict:
        if HOT_CACHE.exists():
            data = json.loads(HOT_CACHE.read_text())
            return data.get(self.mission_id, {})
        return {}

    def _save_hot(self):
        all_hot = {}
        if HOT_CACHE.exists():
            all_hot = json.loads(HOT_CACHE.read_text())
        all_hot[self.mission_id] = self.hot
        HOT_CACHE.write_text(json.dumps(all_hot, indent=2))

    def _load_index(self) -> Dict:
        if INDEX_FILE.exists():
            return json.loads(INDEX_FILE.read_text())
        return {"missions": {}}

    def _save_index(self):
        INDEX_FILE.write_text(json.dumps(self.index, indent=2))

    def store_finding(self, finding: Dict[str, Any], raw_text: str, importance: float = 1.0):
        """Store with automatic tiering and summarization."""
        fid = _hash(raw_text + str(finding.get("timestamp", "")))
        summary = _summarize(raw_text)

        entry = {
            "id": fid,
            "timestamp": datetime.utcnow().isoformat(),
            "mission": self.mission_id,
            "summary": summary,
            "metadata": finding,
            "full_hash": _hash(raw_text),
            "token_estimate": len(raw_text.split()) // 4  # rough
        }

        # Hot tier (recent/high importance)
        if importance >= 0.7 or len(self.hot) < 50:
            self.hot[fid] = entry
            self._save_hot()

        # Always write to warm archive (compressed)
        with open(WARM_ARCHIVE, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Update retrieval index (simple keyword index for now)
        keywords = set(re.findall(r'\b[a-zA-Z]{4,}\b', (summary + " " + str(finding)).lower()))
        self.index.setdefault(self.mission_id, {})[fid] = list(keywords)[:30]
        self._save_index()

    def retrieve(self, query: str, max_results: int = 8, max_tokens: int = 2000) -> List[Dict]:
        """Token-aware retrieval from hot + warm tiers."""
        q_lower = query.lower()
        candidates = []

        # Hot first (fast)
        for fid, entry in self.hot.items():
            if any(k in q_lower for k in self.index.get(self.mission_id, {}).get(fid, [])):
                candidates.append((2.0, entry))  # boost for hot

        # Warm archive (scanned)
        if WARM_ARCHIVE.exists():
            with open(WARM_ARCHIVE) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry["mission"] == self.mission_id:
                            if any(k in q_lower for k in self.index.get(self.mission_id, {}).get(entry["id"], [])):
                                candidates.append((1.0, entry))
                    except:
                        continue

        # Rank + token budget
        candidates.sort(reverse=True, key=lambda x: x[0])
        results = []
        total_tokens = 0
        for score, entry in candidates:
            est = entry.get("token_estimate", 100)
            if total_tokens + est > max_tokens:
                break
            results.append(entry)
            total_tokens += est

        return results

    def get_mission_summary(self) -> Dict:
        """Returns compressed overview for DELTA-style synthesis."""
        return {
            "mission": self.mission_id,
            "hot_items": len(self.hot),
            "estimated_tokens_hot": sum(e.get("token_estimate", 0) for e in self.hot.values()),
            "last_updated": max((e["timestamp"] for e in self.hot.values()), default="never")
        }

# Convenience for agents
def get_memory(mission_id: str) -> HierarchicalMemory:
    return HierarchicalMemory(mission_id)

if __name__ == "__main__":
    mem = get_memory("sedona-2026-05-28")
    mem.store_finding(
        {"source": "CHARLIE", "type": "Black Hawk activity"},
        "Multiple UH-60 Black Hawks observed at KSEZ regional on May 4 2026 performing low level operations over red rocks. Confirmed via airport social media and multiple eyewitness videos.",
        importance=0.95
    )
    print("Memory system operational. Mission summary:", mem.get_mission_summary())