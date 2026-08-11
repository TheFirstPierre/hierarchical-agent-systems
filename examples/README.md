# Examples

Sample outputs for documentation and CI checks.  
Not live production collects unless regenerated.

| File | Source |
|------|--------|
| `pipeline_stress_prediction.json` | `pipelines/python/predict_mortgage_default.py --scenario stress` |
| `recursive_learner_status.json` | Shape of `recursive_learner.py status` after logged outcomes |
| `telemetry_coupled_anomaly_report.json` | Synthetic telemetry swarm deliverable (coupled anomaly) |
| `zero_trust_handoff_package.json` | Layer-1 → Layer-2 handoff matching `schemas/handoff.schema.json` |

## Regenerate

```bash
python pipelines/python/predict_mortgage_default.py --scenario stress --serious --json \
  > examples/pipeline_stress_prediction.json

cd swarms/telemetry && pip install -r requirements.txt
python -m yavapai_swarm activate --window 6h --out ../../examples/telemetry_live.json -y
```

## Expected shapes

- **Pipeline prediction** — `scenario`, `inputs`, `predictions.total_delinq_30plus_pct`
- **Telemetry report** — `coupled_anomalies[]` with `real` / `proxy` / `synthetic` labels
- **Handoff package** — `payload`, `provenance`, `confidence`, `dissent`, `sources`, `verification_hooks`
