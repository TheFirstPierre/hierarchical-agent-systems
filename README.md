# Hierarchical Multi-Agent Systems

Austin Jackson  
[GitHub](https://github.com/TheFirstPierre) · [X](https://x.com/TheFirstPierre)

Layered multi-agent architectures with mandatory verification at boundaries, zero-trust handoffs, social-signal extraction, quantitative recursive pipelines, live telemetry fusion, and controlled self-evolution protocols.

---

## Structure

```
ARCHITECTURE.md / DESIGN_PHILOSOPHY.md   System overview + governing principles

architecture/
  hierarchical-swarm.md                  Four-layer agent architecture
  zero-trust-handoff.md                  Inter-layer contract
  ensemble-probability.md                Ensemble formulation

schemas/
  handoff.schema.json                    Machine-readable handoff contract

x-api/
  social-signal-patterns.md              Collection, extraction, hygiene

agents/
  narrative-deconstruction-agent.md      Media / narrative protocol
  blueprint-forge.md                     Engineering drawing / GD&T protocol
  shadow/                                Recursive multi-turn analysis agent (code)

swarms/
  telemetry/                             Cross-domain telemetry fusion swarm (code)

protocols/
  sesp/                                  Self-evolving swarm protocol (code)

extractors/
  echo/                                  Document / page extraction helpers (code)

pipelines/
  python/                                Ingestion + recursive learner + risk model

tools/
  glass-x/                               Local X composition + virality matrix (code)

examples/                                Sample outputs for docs and CI
materials-systems-note.md                Precision-systems constraints
```

---

## Principles

1. Hierarchy with verification at every boundary  
2. Zero-trust handoffs — prior layers are never assumed correct  
3. Active bias and narrative detection as first-class components  
4. Explicit self-improvement loops (pipelines + SESP)  
5. Physical and mathematical consistency as constraints  
6. Real telemetry labeled honestly (`real` / `proxy` / `synthetic`)  
7. Documentation written to be executable  

---

## Quick starts

### Pipelines

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python pipelines/python/predict_mortgage_default.py --scenario base --serious
python pipelines/python/recursive_learner.py status
```

### Telemetry swarm

```bash
cd swarms/telemetry && pip install -r requirements.txt
python run.py
python -m yavapai_swarm collect-real --window 6h --json -y
```

### SHADOW agent

```bash
cd agents/shadow && pip install -r requirements.txt
python run.py activate --max-turns 5 --out report.json -y
```

### Glass X

```bash
cd tools/glass-x && pip install -r requirements.txt
python run.py
```

---

## Examples

Sample outputs in [`examples/`](examples/):

- Quantitative stress prediction JSON
- Recursive learner status shape
- Synthetic coupled-anomaly telemetry report
- Zero-trust handoff package (schema-aligned)

See [`examples/README.md`](examples/README.md) for regeneration commands.

CI on `main` runs `python -m compileall` over packages, validates handoff schema/examples, and smokes the illustrative pipeline.

---

Work is inspectable and intended to be extended.
