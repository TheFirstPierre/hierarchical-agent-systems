#!/usr/bin/env python3
"""
ECHO Helper - Small utility for swarm agents to request ECHO services.

This represents the "callable helper function" concept.
In a real swarm run, agents would spawn ECHO using the protocol
and pass it requests in the standardized format.
"""

from typing import Dict, Any, Optional
import json

def request_echo(
    url: str,
    mode: str = "auto",
    selector: Optional[str] = None,
    extract_tables: bool = False,
    instructions: str = ""
) -> Dict[str, Any]:
    """
    Standardized way for swarm agents to request parsing from ECHO.

    This function is the Python equivalent of the "ECHO REQUEST" protocol.

    In practice, an agent would:
    1. Call this (or format the equivalent text request)
    2. Spawn an ECHO subagent with the echo_agent_prompt.md
    3. Pass the returned dict as the request

    Returns a structured request object that can be serialized and sent to ECHO.
    """
    request = {
        "type": "ECHO_REQUEST",
        "url": url,
        "mode": mode,
        "selector": selector,
        "extract_tables": extract_tables,
        "instructions": instructions or "Return clean, low-noise main content."
    }
    return request


def format_echo_request_for_prompt(request: Dict[str, Any]) -> str:
    """Convert the request dict into the exact text format used in swarm prompts."""
    lines = [
        "ECHO REQUEST",
        "",
        f"URL: {request['url']}",
        f"MODE: {request['mode']}",
    ]
    if request.get("selector"):
        lines.append(f"SELECTOR: {request['selector']}")
    lines.append(f"EXTRACT_TABLES: {str(request['extract_tables']).lower()}")
    if request.get("instructions"):
        lines.append(f"INSTRUCTIONS: {request['instructions']}")
    return "\n".join(lines)


# Example usage that agents can copy
if __name__ == "__main__":
    req = request_echo(
        url="https://burlison.house.gov/media/press-releases/burlison-presses-mitre-answers-uap-records-ffrdc-accountability-and-compliance",
        mode="html",
        selector="#main-content",
        extract_tables=False,
        instructions="Extract the full legislative interrogatories section cleanly."
    )

    print("Generated ECHO Request:")
    print(format_echo_request_for_prompt(req))
    print("\nJSON version:")
    print(json.dumps(req, indent=2))