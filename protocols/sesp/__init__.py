"""
SESP - Self-Evolving Swarm Protocol

High-level combined interface for layering technical privacy, discovery expansion,
and hierarchical memory on top of your real multi-agent OSINT stack.

Primary recommended entry point:

    from osint_swarm.helpers.osint_parser import call_echo
    from swarm_evolving_protocol import SESPMission

    sesp = SESPMission("ALPHA", mission_id="sedona-2026-05-29", real_backend=call_echo)

    result = sesp.enhanced_echo("https://important.url", extract_tables=True)
    sesp.check_ip_safety()
    sesp.memory_summary()
    sesp.reload()   # reload all SESP modules (dev use)
"""

from __future__ import annotations
from typing import Callable, Optional, Any
import importlib
import sys

__version__ = "1.1.0"

# Re-export the core integration primitives
from .integrations.swarm_launcher_hook import wrap_with_sesp, enhance_swarm_agent

__all__ = [
    "SESPMission",
    "wrap_with_sesp",
    "enhance_swarm_agent",
    "reload_sesp",
]


class SESPMission:
    """
    Combined, ergonomic wrapper that gives you one object with:

        - .enhanced_echo(...)          → your real backend with all SESP layers
        - .check_ip_safety()
        - .memory_summary()
        - .protector
        - .memory
        - .reload()                    → hot-reload the SESP protocol modules

    This is the cleanest way to use the full stack.
    """

    def __init__(
        self,
        agent_name: str = "ALPHA",
        mission_id: str = "default",
        real_backend: Optional[Callable] = None,
    ):
        self.agent_name = agent_name
        self.mission_id = mission_id

        if real_backend is None:
            # Fallback to internal simulation (for testing SESP in isolation)
            self._enhanced = enhance_swarm_agent(
                agent_name=agent_name,
                mission_id=mission_id,
                real_backend=None,
            )["enhanced_query"]
            self._is_real = False
        else:
            self._enhanced = wrap_with_sesp(
                real_backend=real_backend,
                agent_name=agent_name,
                mission_id=mission_id,
            )
            self._is_real = True

        # Bind the most frequently used things directly
        self.enhanced_echo = self._enhanced
        self.protector = getattr(self._enhanced, "sesp_protector", None)
        self.memory = getattr(self._enhanced, "sesp_memory", None)

        # Also expose the raw enhancer dict for advanced access
        self._raw = enhance_swarm_agent(
            agent_name=agent_name,
            mission_id=mission_id,
            real_backend=real_backend,
        )

    # --- Ergonomic shortcuts the user explicitly asked for ---

    def check_ip_safety(self) -> str:
        """Quick public IP safety check (VPN/Tor status)."""
        if self.protector is not None:
            return self.protector.check_ip_safety()
        # Fallback for simulation mode
        return "Protector not available in simulation mode."

    def memory_summary(self) -> dict:
        """Return current mission memory statistics."""
        if self.memory is not None:
            return self.memory.get_mission_summary()
        # Fallback
        return self._raw.get("memory_summary", {})

    def reload(self) -> str:
        """
        Hot-reload all SESP modules.

        Extremely useful when you are actively editing the protocol
        (guardrails, memory, discovery, hook) while a swarm is running.
        """
        return reload_sesp()

    # --- Pass-through / introspection ---

    def __call__(self, *args, **kwargs) -> Any:
        """Allow using the SESPMission instance directly as the enhanced callable."""
        return self.enhanced_echo(*args, **kwargs)

    def __repr__(self) -> str:
        kind = "real" if self._is_real else "simulation"
        return f"<SESPMission agent={self.agent_name} mission={self.mission_id} backend={kind}>"


def reload_sesp() -> str:
    """
    Reload every SESP submodule.

    Usage:
        from swarm_evolving_protocol import reload_sesp
        reload_sesp()

    Or via the session:
        sesp.reload()
    """
    package = "swarm_evolving_protocol"

    modules_to_reload = [
        f"{package}",
        f"{package}.integrations",
        f"{package}.integrations.swarm_launcher_hook",
        f"{package}.modules",
        f"{package}.modules.security",
        f"{package}.modules.security.guardrails",
        f"{package}.modules.memory",
        f"{package}.modules.memory.hierarchical_store",
        f"{package}.modules.discovery",
        f"{package}.modules.discovery.keyword_expander",
        f"{package}.core",
    ]

    reloaded = []
    for mod_name in modules_to_reload:
        if mod_name in sys.modules:
            try:
                importlib.reload(sys.modules[mod_name])
                reloaded.append(mod_name)
            except Exception as e:
                reloaded.append(f"{mod_name} (error: {e})")

    return f"SESP reload complete. Reloaded: {', '.join(reloaded)}"


# Convenience alias matching common user mental model
create_sesp_mission = SESPMission

