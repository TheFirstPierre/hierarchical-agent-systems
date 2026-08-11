"""
Token budget tracker for long-running shadow agent turns.

Zero means unlimited: max_tokens=0, stop_ratio=0.00 disables ratio stops.
Missions end only on duration or a positive max_turns cap.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English prose."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def unlimited_tokens(max_tokens: int | None) -> bool:
    return max_tokens is None or max_tokens <= 0


def unlimited_turns(max_turns: int) -> bool:
    return max_turns <= 0


@dataclass
class TokenBudget:
    max_tokens: int = 0
    stop_ratio: float = 0.00
    briefing_reserve: int = 600
    used: int = 0
    per_turn: list[dict] = field(default_factory=list)

    @property
    def unlimited(self) -> bool:
        return unlimited_tokens(self.max_tokens)

    @property
    def stop_threshold(self) -> int | None:
        if self.unlimited:
            return None
        if self.stop_ratio <= 0:
            return self.max_tokens
        return int(self.max_tokens * self.stop_ratio)

    @property
    def remaining(self) -> int | None:
        if self.unlimited:
            return None
        return max(0, self.max_tokens - self.used)

    @property
    def can_continue(self) -> bool:
        if self.unlimited:
            return True
        threshold = self.stop_threshold or self.max_tokens
        reserve = 0 if self.stop_ratio <= 0 else self.briefing_reserve
        return self.used < (threshold - reserve)

    def charge(self, turn: int, action: str, content: str | dict) -> int:
        if isinstance(content, dict):
            import json
            text = json.dumps(content, default=str)
        else:
            text = content
        cost = estimate_tokens(text) + 50  # overhead per turn
        self.used += cost
        self.per_turn.append({
            "turn": turn,
            "action": action,
            "tokens_estimated": cost,
            "cumulative": self.used,
            "remaining": self.remaining,
        })
        return cost

    def summary(self) -> dict:
        return {
            "max_tokens": self.max_tokens,
            "unlimited": self.unlimited,
            "stop_ratio": self.stop_ratio,
            "stop_threshold": self.stop_threshold,
            "briefing_reserve": self.briefing_reserve,
            "tokens_used": self.used,
            "tokens_remaining": "unlimited" if self.unlimited else self.remaining,
            "per_turn": self.per_turn,
        }