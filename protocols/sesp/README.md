# Self-Evolving Swarm Protocol (SESP)

Layer for controlled capability growth on multi-agent systems:

1. **Discovery expansion** — keyword / correlation expansion with novelty scores  
2. **Hierarchical memory** — hot / warm / cold tiers with token-aware retrieval  
3. **Gated evolution** — structured proposals, review, reversible application with backups  
4. **Technical privacy tools** — export-time redaction and query hygiene (never filters user-facing intel)

## Integration sketch

```python
from protocols.sesp.integrations.swarm_launcher_hook import wrap_with_sesp

enhanced = wrap_with_sesp(
    real_backend=your_callable,
    agent_name="ALPHA",
    mission_id="mission-001",
)
result = enhanced(...)
```

All evolutions require explicit approval. Runtime logs/memory are local and gitignored.
