"""
Project Glass X - Virality Matrix Engine

This is the heart of the tool. It scores draft posts in real time and gives
specific, actionable feedback on composition, hooks, length, CTA, etc.

Design goals:
- Works 100% offline (no API needed for basic use)
- Fast (<5ms)
- Transparent — every point is explained
- Tunable (we'll expose weights later)
- Personalized later using the user's actual historical performance
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ViralityResult:
    total: int                    # 0-100
    grade: str                    # A+ / A / B+ etc.
    breakdown: list[dict[str, Any]]
    suggestions: list[str]
    ideal_length_band: tuple[int, int]
    predicted_engagement_boost: float  # e.g. 1.4x relative to average


def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _has_strong_hook(text: str) -> bool:
    """Detects common high-performing openers."""
    t = text.lower().strip()
    strong_patterns = [
        r"^\d+[\s\.\)]",                    # "7 ways", "3 reasons"
        r"^what if", r"^how to", r"^why ",
        r"^the ",                           # "The brutal truth about..."
        r"^i just", r"^just realized",
        r"^everyone is", r"^nobody talks about",
        r"^stop ", r"^never ",
        r"^\?",                             # starts with question
    ]
    return any(re.search(p, t) for p in strong_patterns)


def _has_question_or_cta(text: str) -> bool:
    t = text.lower()
    return (
        "?" in t
        or any(x in t for x in ["what do you think", "thoughts?", "agree?", "your take", "comment below"])
        or re.search(r"\b(reply|rt|retweet|like|follow|share)\b", t) is not None
    )


def _emoji_density(text: str) -> float:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    emojis = len(emoji_pattern.findall(text))
    words = max(_count_words(text), 1)
    return emojis / words


def _hashtag_count(text: str) -> int:
    return len(re.findall(r"#\w+", text))


def _readability_score(text: str) -> float:
    """Simple proxy: shorter sentences + line breaks = better on X."""
    sentences = max(len(re.split(r"[.!?]+", text)), 1)
    words = _count_words(text)
    avg_words_per_sentence = words / sentences
    line_breaks = text.count("\n")
    score = 10
    if avg_words_per_sentence < 18:
        score += 8
    if line_breaks >= 1:
        score += 6
    if line_breaks >= 2:
        score += 4
    return min(score, 20)


def score_post(
    text: str,
    has_media: bool = False,
    is_thread: bool = False,
    hour: int | None = None,           # 0-23 local time (for timing bonus)
) -> ViralityResult:
    """
    Main entry point. Returns a rich scoring object.
    """
    if not text or not text.strip():
        return ViralityResult(
            total=0, grade="F", breakdown=[], suggestions=["Write something first"],
            ideal_length_band=(120, 160), predicted_engagement_boost=1.0
        )

    char_count = len(text)
    word_count = _count_words(text)
    breakdown = []
    suggestions: list[str] = []
    score = 42  # base

    # === LENGTH (very important on X) ===
    ideal_min, ideal_max = (110, 175) if not is_thread else (60, 140)
    length_score = 0
    if ideal_min <= char_count <= ideal_max:
        length_score = 22
        breakdown.append({"factor": "Length", "points": 22, "note": f"Perfect ({char_count} chars)"})
    elif char_count < 80:
        length_score = 6
        breakdown.append({"factor": "Length", "points": 6, "note": "Too short — weak signal"})
        suggestions.append("Aim for 110-175 characters for single posts (higher perceived value)")
    elif char_count > 220:
        length_score = 8
        breakdown.append({"factor": "Length", "points": 8, "note": "Long — consider splitting into a thread"})
        suggestions.append("Break this into a 2-4 tweet thread for much better reach")
    else:
        length_score = 15
        breakdown.append({"factor": "Length", "points": 15, "note": f"Decent ({char_count} chars)"})
    score += length_score

    # === STRONG HOOK (first 15 chars / first line matter enormously) ===
    if _has_strong_hook(text):
        score += 18
        breakdown.append({"factor": "Hook", "points": 18, "note": "Strong opening detected"})
    else:
        breakdown.append({"factor": "Hook", "points": 0, "note": "Weak / generic opener"})
        suggestions.append("Start with a number, question, bold claim, or 'How to' / 'Why' pattern")

    # === ENGAGEMENT TRIGGER (question or explicit CTA) ===
    if _has_question_or_cta(text):
        score += 14
        breakdown.append({"factor": "Engagement", "points": 14, "note": "Has question or CTA"})
    else:
        breakdown.append({"factor": "Engagement", "points": 0, "note": "No clear reason for people to reply"})
        suggestions.append("Add a question or direct ask in the last line (\"What's your take?\")")

    # === MEDIA BONUS ===
    if has_media:
        score += 13
        breakdown.append({"factor": "Media", "points": 13, "note": "Visual content attached"})
    else:
        breakdown.append({"factor": "Media", "points": 0, "note": "No image or video"})
        suggestions.append("Add a relevant image or short video — usually +30-80% reach")

    # === HASHTAG DISCIPLINE ===
    ht = _hashtag_count(text)
    if 0 <= ht <= 2:
        score += 7
        breakdown.append({"factor": "Hashtags", "points": 7, "note": f"Good ({ht})"})
    else:
        breakdown.append({"factor": "Hashtags", "points": -4, "note": f"Too many ({ht})"})
        suggestions.append("Use 0-2 highly relevant hashtags. More looks spammy.")

    # === READABILITY (line breaks, sentence length) ===
    read_bonus = _readability_score(text)
    score += read_bonus
    breakdown.append({"factor": "Readability", "points": read_bonus, "note": "Line breaks & sentence flow"})

    # === EMOJI DENSITY (sweet spot) ===
    density = _emoji_density(text)
    if 0.03 <= density <= 0.12:
        score += 6
        breakdown.append({"factor": "Emoji", "points": 6, "note": "Good visual breathing room"})
    elif density > 0.2:
        breakdown.append({"factor": "Emoji", "points": -3, "note": "Over-emoji'd"})
        suggestions.append("Tone down emojis — they can look desperate when overused")

    # === THREAD BONUS ===
    if is_thread:
        score += 9
        breakdown.append({"factor": "Thread", "points": 9, "note": "Thread format (higher total reach potential)"})

    # === TIMING BONUS (very rough, will be replaced by real data) ===
    timing_bonus = 0
    if hour is not None:
        # Rough "good windows" for many professional/creator audiences
        if 8 <= hour <= 11 or 19 <= hour <= 21:
            timing_bonus = 5
            breakdown.append({"factor": "Timing (general)", "points": 5, "note": "Historically strong window"})
        elif 0 <= hour <= 5:
            timing_bonus = -6
            breakdown.append({"factor": "Timing (general)", "points": -6, "note": "Dead hours for most audiences"})
    score += timing_bonus

    # Final normalization
    total = max(0, min(100, int(score)))

    # Grade
    if total >= 92: grade = "A+"
    elif total >= 85: grade = "A"
    elif total >= 78: grade = "B+"
    elif total >= 70: grade = "B"
    elif total >= 60: grade = "C+"
    else: grade = "C"

    # Predicted relative performance (very rough model)
    boost = 0.6 + (total / 100) * 1.1
    if has_media:
        boost *= 1.15
    if is_thread:
        boost *= 1.25
    boost = round(boost, 1)

    # Deduplicate & prioritize suggestions
    suggestions = list(dict.fromkeys(suggestions))[:4]

    if not suggestions:
        suggestions.append("This draft is already strong. Consider A/B testing two versions.")

    return ViralityResult(
        total=total,
        grade=grade,
        breakdown=breakdown,
        suggestions=suggestions,
        ideal_length_band=(ideal_min, ideal_max),
        predicted_engagement_boost=boost,
    )


def explain_grade(grade: str) -> str:
    mapping = {
        "A+": "Exceptional. High chance of strong engagement for your account.",
        "A":  "Very good. Should perform well.",
        "B+": "Solid. A few tweaks could push it into A territory.",
        "B":  "Average to good. Address the suggestions.",
        "C+": "Below average. Needs work before scheduling.",
        "C":  "Weak signal. Major improvements recommended.",
    }
    return mapping.get(grade, "")


# =============================================================================
# FUTURE: Personalization Layer (Core Competitive Advantage #2 + #9)
# =============================================================================
#
# This directly supports two major advantages:
# - Personalization That Actually Learns From *You*
# - Reduced Long-Term Dependency (Skill Amplification)
#
# Current version uses universal heuristics.
#
# Long-term moat: Per-account / per-user performance models.
#
# Planned evolution:
#   1. When a user connects an X account and posts through Glass X,
#      we log basic outcomes (impressions, engagement rate, replies, etc.).
#   2. Over time we compute account-specific adjustments, e.g.:
#        - "Questions in first line → +28% replies for this account"
#        - "Image + question combo is unusually strong for this audience"
#        - "Your optimal length is actually 95-130 chars (not the generic 110-175)"
#   3. The score_post() function will eventually accept an optional
#      `account_id` or `performance_profile` and re-weight factors accordingly.
#
# This turns Glass X from "a scoring tool" into "the only tool that truly
# understands what works for *your* specific audience and voice".
#
# See COMPETITIVE_ADVANTAGES.md (advantages #2 and #9).
# =============================================================================


def get_personalization_note() -> str:
    """Placeholder for future personalized insight messaging."""
    return "Personalized insights will appear here once you connect an account and publish a few posts."
