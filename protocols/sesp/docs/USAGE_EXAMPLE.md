# SESP Usage Example: Enhancing a regional-Style Military/UAP Deep Dive

## Step 1: Wire SESP Directly to Your Real Swarm
```python
from osint_swarm.helpers.osint_parser import call_echo
from swarm_evolving_protocol.integrations.swarm_launcher_hook import wrap_with_sesp

# Full production link — real work + SESP protections + memory + expansion
enhanced = wrap_with_sesp(
    real_backend=call_echo,
    agent_name="ALPHA",
    mission_id="sedona-military-followup-2026-05-28"
)
```

## Step 2: Use It Like Normal call_echo (Everything Else Is Automatic)
```python
# Real fetches happen. SESP runs silently underneath:
# - Outbound privacy sanitization
# - Discovery expansion for ALPHA/CHARLIE
# - Every result is stored + summarized in the hierarchical memory

result = enhanced(
    "https://www.af.mil/news/sedona-black-hawk-activity",
    extract_tables=True,
    ocr_fallback=True
)

print(result["main_text"][:1200])
print("SESP attached:", result.get("_sesp"))
```

## Step 3: CHARLIE + Memory
CHARLIE can store new X/ADS-B findings directly into the mission's hierarchical memory with one call (via the enhancer).

## Step 4: DELTA Synthesis
```python
context = enhancer["get_relevant_memory"]("Black Hawk KSEZ May 4", max_tokens=1500)
# Returns only the most relevant, already-summarized findings within token budget.
```

## Self-Evolution in Action (Example Proposal an Agent Could Output)
An agent noticing the keyword expander missed "AFSOC U-28A Draco" could output a proposal using the schema to add better AFSOC-specific correlation logic.

All such proposals are logged, reviewed, and only applied with backup + user sign-off.

This turns every future swarm deployment into a compounding intelligence asset while protecting your interests.