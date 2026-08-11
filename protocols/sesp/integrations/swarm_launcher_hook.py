#!/usr/bin/env python3
"""
SESP Integration Hook — Real Swarm Adapter

This is the primary integration point that wires the Self-Evolving Swarm Protocol
(technical privacy, discovery expansion, hierarchical memory) on top of your
existing multi-agent OSINT stack.

Real entry point of your swarm:
    from osint_swarm.helpers.osint_parser import call_echo
    # or
    from osint_swarm.swarm_bootstrap import call_echo, SwarmSession

Usage (recommended):

    from osint_swarm.helpers.osint_parser import call_echo
    from swarm_evolving_protocol.integrations.swarm_launcher_hook import wrap_with_sesp

    # Wire SESP layers around your real swarm capability
    enhanced_echo = wrap_with_sesp(
        real_backend=call_echo,
        agent_name="ALPHA",
        mission_id="mission-001"
    )

    # Now use it exactly like the original call_echo — but with full SESP benefits
    result = enhanced_echo(
        "https://www.congress.gov/some-important-document",
        extract_tables=True,
        ocr_fallback=True
    )
    # result is the real dict from the swarm + SESP metadata attached

    # You also get direct access to the protector and memory:
    # enhanced_echo.sesp_protector.check_ip_safety()
    # enhanced_echo.sesp_memory.get_mission_summary()
"""

from typing import Callable, Any, Dict, Optional
import inspect

# Clean relative imports now that the package has proper __init__.py files
from ..modules.discovery.keyword_expander import expand_keywords
from ..modules.memory.hierarchical_store import get_memory
from ..modules.security.guardrails import OutboundProtection


def wrap_with_sesp(
    real_backend: Callable,
    agent_name: str = "ALPHA",
    mission_id: str = "default",
    auto_expand: bool = True,
    auto_store: bool = True,
) -> Callable:
    """
    Wrap any real swarm callable (e.g. call_echo) with full SESP capabilities.

    This is the function that actually "links" SESP to your live swarm.

    Applied layers:
    - OutboundProtection (sanitizes any free-text instructions before they leave)
    - Automatic keyword expansion suggestions for ALPHA/CHARLIE (printed + logged)
    - Automatic storage of every successful result into the hierarchical memory
    - Full access to protector and memory via attributes on the returned wrapper

    Args:
        real_backend: Your actual swarm function (most commonly `call_echo`).
        agent_name: "ALPHA", "CHARLIE", etc. Controls expansion behavior.
        mission_id: Persistent mission identifier for memory + audit.
        auto_expand: Whether to run discovery expansion for ALPHA/CHARLIE.
        auto_store: Whether to persist results into hierarchical memory.

    Returns:
        A callable with the same signature as `real_backend`, plus:
            .sesp_protector
            .sesp_memory
            .sesp_agent_name
            .sesp_mission_id
    """
    mem = get_memory(mission_id)
    protector = OutboundProtection(mission_id)

    def sesp_wrapped(*args, **kwargs) -> Any:
        """
        Wrapped version of the real backend.
        All SESP protections and enhancements are applied transparently.
        """
        # --- 1. Outbound protection on any string arguments (instructions, queries, etc.) ---
        sanitized_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, str):
                sanitized_kwargs[k] = protector.prepare_query(v)
            else:
                sanitized_kwargs[k] = v

        # Sanitize positional string args (rare for call_echo, but defensive)
        sanitized_args = tuple(
            protector.prepare_query(a) if isinstance(a, str) else a for a in args
        )

        # Reconstruct a "query" representation for expansion / logging
        query_for_expansion = ""
        if args and isinstance(args[0], str):
            query_for_expansion = args[0]
        elif "instructions" in sanitized_kwargs:
            query_for_expansion = sanitized_kwargs["instructions"]
        elif "url" in sanitized_kwargs:  # fall back for clarity in logs
            query_for_expansion = sanitized_kwargs.get("url", "")

        # --- 2. Discovery expansion (only for ALPHA / CHARLIE, and only on text) ---
        if auto_expand and agent_name in ["ALPHA", "CHARLIE"] and query_for_expansion:
            try:
                expansions = expand_keywords([query_for_expansion], mission_id=mission_id)
                novel = expansions.get("total_novel", 0)
                if novel > 0:
                    print(f"[SESP] {agent_name} discovered {novel} novel correlated terms.")
                    # Store the expansion event itself as lightweight memory
                    if auto_store:
                        mem.store_finding(
                            {"agent": agent_name, "action": "discovery_expansion", "query": query_for_expansion},
                            f"Expansion produced {novel} novel terms for mission {mission_id}",
                            importance=0.4,
                        )
            except Exception as e:
                print(f"[SESP] Expansion warning (non-fatal): {e}")

        # --- 3. Call the real backend ---
        result = real_backend(*sanitized_args, **sanitized_kwargs)

        # --- 4. Automatic memory storage of real results ---
        if auto_store and isinstance(result, dict) and result.get("status") == "success":
            try:
                main_text = result.get("main_text", "") or result.get("content", "")
                metadata = {
                    "agent": agent_name,
                    "action": "real_fetch",
                    "url": result.get("url") or (args[0] if args else None),
                    "source_domain": result.get("source_domain"),
                    "word_count": result.get("word_count"),
                    "entities_keys": list(result.get("entities", {}).keys()) if result.get("entities") else [],
                }
                importance = 0.85 if agent_name == "ALPHA" else 0.7

                mem.store_finding(metadata, main_text, importance=importance)
            except Exception as e:
                print(f"[SESP] Memory storage warning (non-fatal): {e}")

        # Attach lightweight SESP provenance if the result is a dict
        if isinstance(result, dict):
            result.setdefault("_sesp", {})
            result["_sesp"].update({
                "agent": agent_name,
                "mission": mission_id,
                "protected": True,
                "memory_stored": auto_store,
            })

        return result

    # Attach convenient accessors directly on the wrapper function
    sesp_wrapped.sesp_protector = protector
    sesp_wrapped.sesp_memory = mem
    sesp_wrapped.sesp_agent_name = agent_name
    sesp_wrapped.sesp_mission_id = mission_id

    # Also expose the raw helpers for advanced use
    sesp_wrapped.check_ip_safety = protector.check_ip_safety
    sesp_wrapped.get_privacy_recommendations = protector.get_safe_curl  # slight misnomer but useful

    return sesp_wrapped


def enhance_swarm_agent(
    agent_name: str = "ALPHA",
    mission_id: str = "default",
    real_backend: Optional[Callable] = None,
):
    """
    High-level convenience wrapper.

    When `real_backend` is provided (recommended), returns a ready-to-use
    enhanced version of your real swarm primitive (usually `call_echo`).

    When `real_backend` is None, falls back to the original internal simulation
    (useful for testing SESP modules in isolation).
    """
    mem = get_memory(mission_id)
    protector = OutboundProtection(mission_id)

    if real_backend is not None:
        enhanced_callable = wrap_with_sesp(
            real_backend=real_backend,
            agent_name=agent_name,
            mission_id=mission_id,
        )

        def get_context_for_synthesis(query: str, max_tokens: int = 1800):
            return mem.retrieve(query, max_results=6, max_tokens=max_tokens)

        return {
            "enhanced_echo": enhanced_callable,           # primary thing you call
            "enhanced_call": enhanced_callable,           # alias
            "get_relevant_memory": get_context_for_synthesis,
            "memory_summary": mem.get_mission_summary(),
            "outbound_protector": protector,
            "check_ip_safety": protector.check_ip_safety,
            "memory": mem,
        }

    # --- Legacy simulation path (no real backend) ---
    def enhanced_search_or_query(original_query: str, **kwargs):
        protected_query = protector.prepare_query(original_query)

        if agent_name in ["ALPHA", "CHARLIE"]:
            try:
                expansions = expand_keywords([protected_query], mission_id=mission_id)
                print(f"[SESP] {agent_name} auto-expanded query with {expansions.get('total_novel', 0)} novel terms.")
            except Exception:
                pass

        result_text = f"[SIMULATED] {protected_query}"
        mem.store_finding(
            {"agent": agent_name, "action": "simulated_search", "query": protected_query},
            result_text,
            importance=0.8 if agent_name == "ALPHA" else 0.6,
        )
        return result_text

    def get_context_for_synthesis(query: str, max_tokens: int = 1800):
        return mem.retrieve(query, max_results=6, max_tokens=max_tokens)

    return {
        "enhanced_query": enhanced_search_or_query,
        "get_relevant_memory": get_context_for_synthesis,
        "memory_summary": mem.get_mission_summary(),
        "outbound_protector": protector,
        "check_ip_safety": protector.check_ip_safety,
        "memory": mem,
    }


# Convenience alias for the most common pattern
create_enhanced_echo = wrap_with_sesp


# ---------------- Self-test / demo ----------------
if __name__ == "__main__":
    print("SESP Real Swarm Link — Self Test\n")

    # Demo 1: Using the adapter with a dummy real backend (no real swarm required for this test)
    def dummy_real_backend(url: str, **kwargs):
        return {
            "url": url,
            "status": "success",
            "main_text": f"Real content from {url} would appear here. Keywords: military, Black Hawk, KSEZ.",
            "word_count": 42,
            "source_domain": "example.gov",
        }

    enhanced = wrap_with_sesp(dummy_real_backend, agent_name="ALPHA", mission_id="sesp-link-test")
    result = enhanced("https://test.example.gov/sedona-military-activity", extract_tables=True)

    print("Result received (real shape + SESP metadata):")
    print("  url:", result.get("url"))
    print("  _sesp:", result.get("_sesp"))
    print("\nMemory summary after call:", enhanced.sesp_memory.get_mission_summary())
    print("\nOutbound protector available:", hasattr(enhanced, "sesp_protector"))

    print("\n---")
    print("To wire your REAL swarm, do this:")
    print("  from osint_swarm.helpers.osint_parser import call_echo")
    print("  from swarm_evolving_protocol.integrations.swarm_launcher_hook import wrap_with_sesp")
    print("  enhanced = wrap_with_sesp(call_echo, agent_name='ALPHA', mission_id='your-mission')")
    print("  result = enhanced('https://real.url.here', extract_tables=True)")