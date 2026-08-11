# Cross-Domain Telemetry Swarm

Multi-agent swarm for fusing public telemetry streams, detecting per-signal anomalies, and elevating **coupled anomalies** where two or more domains deviate together.

## Agents

| Agent | Domain |
|-------|--------|
| ECHO | Aviation & atmospheric (ADS-B and related) |
| TESSA | Energy & infrastructure (grid load proxies) |
| CYBER | Digital & institutional signals |
| VECTOR | Socio-economic & environmental rhythms |

## Modes

- **Real** — public sources only (USGS, OpenSky ADS-B, EIA, etc.), with explicit `real` / `proxy` / `synthetic` labels
- **Scenario** — high-fidelity synthetic generators for offline stress tests

Commands that contact external services default to confirmation prompts (`-y` to skip).

## Quick start

```bash
cd swarms/telemetry
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# dashboard
python run.py

# real public telemetry window
python -m yavapai_swarm activate --real --window 6h --out report.json -y
python -m yavapai_swarm collect-real --window 12h --json -y
```

## Design notes

- Coupled anomalies are first-class deliverables, not post-hoc narrative.
- Signals without a public real-time surface are labeled `NO_PUBLIC_REAL`.
- Cross-domain rules live in the collision engine (e.g. grid stress mirrored by emergency / industrial activity).

Runtime state under `data/` is local and gitignored.
