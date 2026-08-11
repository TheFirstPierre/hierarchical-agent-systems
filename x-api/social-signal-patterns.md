# X / Social Signal Intelligence Patterns

Practical patterns for extracting high-value signal from the X platform (and similar real-time social streams) inside multi-agent systems.

These patterns emphasize precision, rate-limit resilience, bias awareness, and structured output suitable for hierarchical fusion.

---

## 1. Advanced Search Operator Discipline

Effective queries combine multiple operators rather than relying on keyword volume.

Common high-signal constructions:

- Temporal bounding: `since:YYYY-MM-DD` / `until:YYYY-MM-DD` or relative windows
- Engagement filters: `min_faves:N`, `min_retweets:N`, `min_replies:N`
- Conversation and quote tracking: `conversation_id:`, `quoted_tweet_id:`, `filter:quote`
- Account and network scoping: `from:`, `to:`, `@`, list-based targeting
- Content type: `filter:replies`, `filter:self_threads`, `filter:media`, `filter:links`
- Negation and precision: careful use of `-` and exact phrases

**Principle:** Prefer narrow, high-precision queries over broad keyword sweeps. Volume is cheap; relevance and source quality are not.

---

## 2. Multi-Pass Collection Strategy

A single query is rarely sufficient for robust signal.

Typical multi-pass pattern used by collector agents:

1. **Seed pass** — High-engagement or authoritative accounts on the core topic.
2. **Expansion pass** — Quotes, replies, and conversation threads around the highest-signal seeds.
3. **Contrarian / suppressed pass** — Explicitly search for dissenting language, low-engagement but high-credibility accounts, and alternative framings.
4. **Narrative velocity pass** — Time-sliced queries to detect acceleration or decay of specific frames.

Each pass feeds structured records (not raw text dumps) into the next stage.

---

## 3. Structured Extraction Schema

Raw posts are immediately reduced to a consistent schema before any higher analysis:

- Post ID / conversation ID
- Author metadata (followers, verification status, account age proxy, historical reliability if known)
- Timestamp
- Core claim or narrative frame (short summary)
- Engagement metrics
- Media / link presence
- Detected stance or valence (when reliable)
- Source quality tier (pre-assigned or scored)

This schema enables zero-trust handoff and later ensemble aggregation without carrying full conversational noise.

---

## 4. Bias & Narrative Hygiene

Social platforms are high-bias environments. Collector and early analyst layers must:

- Separate volume from credibility
- Explicitly track which frames are being amplified by which networks
- Maintain parallel “official / mainstream” and “dissent / alternative” collection tracks
- Flag coordinated language patterns or sudden synchronized posting
- Avoid treating engagement rank as truth rank

Higher layers (especially narrative/psychological deconstruction) receive both the dominant and the suppressed tracks.

---

## 5. Rate-Limit & Resilience Patterns

Production systems must survive platform constraints:

- Respect documented rate limits with exponential backoff and jitter
- Prefer recent, targeted queries over historical bulk pulls when possible
- Cache and deduplicate aggressively by post ID
- Maintain a small set of high-value “watch” queries that can be refreshed frequently
- Degrade gracefully: when limits are hit, prioritize the highest-signal remaining collection passes

---

## 6. Integration with Hierarchical Swarm

Social signal agents typically sit in Layer 1 as one or more specialized clusters (e.g., “Social Sentiment & Narrative”, “Contrarian / Suppressed Signals”).

Their outputs enter the standard zero-trust handoff package and are subject to:

- Mathematical / consistency verification (Layer 2)
- Narrative and cognitive bias deconstruction (Layer 3)
- Final strategic synthesis (Layer 4)

This prevents social volume or emotional intensity from dominating the final product.

---

## Design Notes

The goal is not to “scrape everything.” The goal is to surface the highest-leverage, best-sourced, and most carefully debiased signals that actually move understanding of the target question.

These patterns are platform-aware but architecture-agnostic. They can be implemented with official APIs, careful search tooling, or hybrid approaches depending on access level.

---

*Operational query libraries, specific account lists, and live collection configurations are omitted.*
