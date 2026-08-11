# Examples

Illustrative outputs for documentation and CI smoke context.  
These are **not** live production collects unless you generate them yourself.

| File | Source |
|------|--------|
| `pipeline_stress_prediction.json` | `pipelines/python/predict_mortgage_default.py --scenario stress` |
| `recursive_learner_status.json` | Shape of `recursive_learner.py status` after logged outcomes |
| `telemetry_coupled_anomaly_report.json` | Synthetic telemetry swarm deliverable (coupled anomaly) |
| `zero_trust_handoff_package.json` | Example Layer-1 → Layer-2 handoff matching `schemas/handoff.schema.json` |

## Regenerate (optional)

```bash
# quantitative pipeline
python pipelines/python/predict_mortgage_default.py --scenario stress --serious --json \
  > examples/pipeline_stress_prediction.json

# telemetry (requires deps + optional network / keys)
cd swarms/telemetry && pip install -r requirements.txt
python -m yavapai_swarm activate --window 6h --out ../../examples/telemetry_live.json -y
```

## Expected shapes

**Pipeline prediction** includes `scenario`, `inputs`, and `predictions.total_delinq_30plus_pct`.

**Telemetry report** prioritizes `coupled_anomalies[]` and labels data as `real` / `proxy` / `synthetic`.

**Handoff package** always carries `payload`, `provenance`, `confidence`, `dissent`, `sources`, and `verification_hooks`.
