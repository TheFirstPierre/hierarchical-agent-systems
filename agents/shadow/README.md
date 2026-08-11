# SHADOW — Recursive Analysis Agent

Standalone multi-turn analysis agent with:

- Recursive learning across turns (seed evolution, term boosts, signal weights)
- Token-budget and stop-ratio controls
- Adaptive seed registry
- Structured JSON mission report + optional PDF briefing

## Quick start

```bash
cd agents/shadow
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python run.py activate --max-turns 5 --out report.json -y
```

External calls default to confirmation prompts. Learning state under `data/` is local and gitignored.

Designed to plug into hierarchical multi-agent stacks as a specialized collector / analyst layer.
