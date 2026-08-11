# Hierarchical Multi-Agent Systems

Austin Jackson  
[GitHub](https://github.com/TheFirstPierre) · [X](https://x.com/TheFirstPierre)

Layered multi-agent architectures with mandatory verification at boundaries, zero-trust handoffs, social-signal extraction, quantitative recursive pipelines, and precision-systems discipline.

---

## Structure

```
ARCHITECTURE.md                          System overview + diagrams
DESIGN_PHILOSOPHY.md                     Governing principles

architecture/
  hierarchical-swarm.md                  Four-layer agent architecture
  zero-trust-handoff.md                  Inter-layer contract specification
  ensemble-probability.md                Core probabilistic formulation

x-api/
  social-signal-patterns.md              Collection, extraction, hygiene

agents/
  narrative-deconstruction-agent.md      Media / narrative analysis protocol
  blueprint-forge.md                     Engineering drawing / GD&T protocol

pipelines/
  methodology.md                         Predictive model notes
  data-ingestion-and-learning.md         Pipeline design notes
  python/
    data_ingestion_optimizer.py          Large-scale ingestion + summarization
    recursive_learner.py                 Prediction → outcome → update loop
    predict_mortgage_default.py          Illustrative risk model
  state/
    example_learned_model_state.json     Example persistent state

schemas/
  handoff.schema.json                    Zero-trust handoff JSON schema

materials-systems-note.md                Transfer from physical precision work
```

---

## Principles

1. Hierarchy with verification at every boundary  
2. Zero-trust handoffs — prior layers are never assumed correct  
3. Active bias and narrative detection as first-class components  
4. Explicit self-improvement loops  
5. Physical and mathematical consistency as constraints  
6. Documentation written to be executable  

---

## Quick start (pipelines)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# illustrative risk model
python pipelines/python/predict_mortgage_default.py --scenario base --serious

# recursive learning status / update
python pipelines/python/recursive_learner.py status
python pipelines/python/recursive_learner.py log \
  --period Q2_2026 --predicted 5.1 --actual 4.8 \
  --unemp 4.3 --mort_rate 6.7 --hpa_yoy 3.8
python pipelines/python/recursive_learner.py update --method re_fit

# compact ingestion summary (CSV/Excel/Parquet)
python pipelines/python/data_ingestion_optimizer.py path/to/data.csv
```

---

Work is inspectable and intended to be extended.
