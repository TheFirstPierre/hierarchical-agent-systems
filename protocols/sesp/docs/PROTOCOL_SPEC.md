# Self-Evolving Swarm Protocol (SESP) v1.0

**Deployed:** 2026-05-28  
**Owner:** User (theophilos) via operator multi-agent stack  
**Purpose:** Enable ALPHA/BRAVO/CHARLIE/DELTA (and future agents) to autonomously expand capabilities in data discovery and resource efficiency.

## Core Principles
1. **User Sovereignty First**: All evolutions require explicit approval. No autonomous actions that could expose, exfiltrate, or harm user data.
2. **Self-Evolution via Proposals**: Agents propose improvements in structured format. A Meta-Reviewer (human or gated script) approves before application.
3. **Evidence-Based**: All changes must be backed by logged experiments, performance metrics, or novel data gains.
4. **Minimal Token/Memory Footprint**: Prioritize compression, summarization, and selective retrieval.
5. **Minimal Oversight Overhead**: The protocol focuses purely on capability expansion and efficiency.

## Pillars

### Technical Security (User-Defined Scope)

**Core Rule (as specified by user)**:  
The user must receive the **raw, complete, unfiltered** output on every topic.  
For no reason should any part of the intelligence delivered to the user be redacted, filtered, or withheld.  
The goal is to make the user the single most informed party possible. "Everyone else gets nothing."

**Therefore**:
- Security exists **only** to prevent external parties (anyone besides the user) from accessing the user's data, location, IP address, or device/Cloudflare identifiers.
- Redaction functions exist **only** for cases where the user wants to safely export or share findings with third parties.
- No redaction or filtering is ever applied to output delivered to the user.

**Core Module**: `modules/security/guardrails.py`

**Current Technical Tools**:
- `sanitize_outgoing_query()` — Reduces fingerprinting when the swarm makes external searches
- `get_privacy_recommendations()` — Practical advice for protecting IP/location/device identifiers during operation
- `redact_location()`, `sanitize_network_identifiers()`, `protect_local_paths()` — For export/sharing use only (clearly labeled)
- `warn_on_sensitive_file_access()` — Protects against accidental local data exposure
- `apply_technical_protections()` — Combined helper for export use only

### Pillar 1: Novel Data Discovery Expansion
**Goal**: Dynamically discover new search terms, correlations, and data sources beyond initial queries.

**Core Module**: `discovery/keyword_expander.py`

**Key Features**:
- Seed keyword input → Cross-correlation engine (co-occurrence from search results + semantic expansion).
- Novel term scoring (novelty = low prior frequency in swarm memory + high relevance signal).
- Automatic query expansion for ALPHA/CHARLIE.
- Example: For "regional military" → discovers "Yavapai County MTR IR-112", "Bradshaw Ranch USFS acquisition 2001", "Luke AFB low-level training routes 2026", "KSEZ Black Hawk May 4 2026" etc.

**Self-Evolution Hook**:
- Agents can propose new correlation heuristics (e.g., "add arXiv co-citation graph for scientific terms").
- Proposals stored in `proposals/` for review.

### Pillar 2: Technical Privacy Protections (User-Defined Scope)

The older "Security & Alignment" pillar was removed per user request. No content filtering, output redaction, or alignment-style guardrails exist or will be proposed.

**What remains (by explicit design):**  
The `modules/security/guardrails.py` module provides **purely technical** protections:
- Outbound query sanitization to reduce fingerprinting of your interests/location when the swarm queries external services
- IP leak detection and privacy-hardened curl helpers
- Export-only redaction tools for location, local paths, and network identifiers (never applied to output you receive)

These tools exist **only** to stop external parties from learning about you. You always receive raw, complete, unfiltered results. See the module docstring for the full philosophy.

### Pillar 3: Novel Memory, Storage & Token Utilization
**Goal**: Maximize useful context while minimizing tokens and storage bloat.

**Core Module**: `memory/hierarchical_store.py`

**Key Features (Initial)**:
- Tiered storage:
  - **Hot (short-term)**: Recent findings (last 72h or current mission) in RAM + small JSON.
  - **Warm**: Summarized episodes (key events, correlations) with vector-like metadata (simple embeddings via hashing or external if available).
  - **Cold (long-term)**: Compressed archives + retrieval index.
- Automatic summarization before storage (using lightweight rules + future LLM calls).
- Token-aware retrieval: Query router returns only top-k relevant compressed chunks.
- Deduplication via content hashing.
- Self-optimization: Track token usage per agent/mission and propose compression strategies.

**Self-Evolution Hook**:
- Agents log "token waste events" and propose new retrieval or summarization algorithms.

## Self-Evolution Mechanism (Meta-Protocol)
1. Any agent can output a `Proposal` in strict JSON format (see `core/proposal_schema.json`).
2. Proposal includes:
   - Change type (new tool / memory strategy / discovery heuristic)
   - Rationale + expected gain (novel data / efficiency)
   - Diff or code patch
   - Test cases / success metrics
   - Risk assessment
3. Meta-Reviewer (initially human via this interface, later script with veto) reviews.
4. Approved changes are applied via controlled `apply_patch.py` (with rollback).
5. All evolutions logged in `evolution_log.jsonl` with cryptographic hash chain for integrity.

## Integration with multi-agent OSINT stack
- ALPHA: Uses discovery expander on every seed query.
- BRAVO: Focuses purely on zero-trust verification.
- CHARLIE: Leverages memory store for historical X/ADS-B patterns + proposes new correlation rules.
- DELTA: Uses hierarchical memory when synthesizing JSON reports; proposes report format improvements.
- New agents can inherit the protocol by importing `sesp.core`.

## Initial Deployment State (v1.0 - 2026-05-28)
- Core spec and schemas created.
- Basic modules implemented (expandable).
- Memory: file-based hierarchical with summarization.
- Example usage tied to regional military deep dive.
- Technical privacy module (`guardrails.py`) retained for outbound protection and export redaction only. No alignment or content filtering present.

## Usage
See `docs/USAGE.md` and `integrations/swarm_launcher_hook.py`.

**User Control**: At any time, user can delete the `proposals/` directory or remove this protocol entirely.

This protocol is designed to grow with the swarm. The security module exists solely for the technical protection of your hard drive, location, IP, and device identifiers — nothing else.