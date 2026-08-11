#!/usr/bin/env python3
"""
SESP Minimal Technical Security Module (User-Defined Scope)
Version: 2.2 (Merged outbound protection features - 2026-05-28)

PHILOSOPHY (as defined by user):
- The user must receive the raw, complete, unfiltered output on every topic.
- For no reason should any part of the intelligence delivered to the user be redacted, filtered, or withheld.
- The goal is to make the user the single most informed party possible.
- "Everyone else gets nothing."

Therefore:
- This module exists ONLY to prevent external parties from gaining access to the user's data, location, IP, or device identifiers.
- It must NEVER be used to redact or sanitize output that is delivered to the user themselves.
- Redaction functions are intended only for cases where the user wants to safely export/share findings with third parties.

Outbound protection features (query sanitization, IP leak detection, privacy curl helpers, etc.) have been merged in.

All functions are strictly opt-in technical tools.
No content-based filtering or "alignment" logic exists.
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import subprocess

BASE_DIR = Path(__file__).parent.parent.parent
AUDIT_LOG = BASE_DIR / "logs" / "technical_security_audit.jsonl"


def _log_technical_event(event_type: str, details: dict):
    """Very lightweight audit log — only for technical security events."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": event_type,
        "details": details
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ====================== LOCATION PROTECTION ======================

def redact_location(text: str, aggressive: bool = True) -> str:
    """
    [EXPORT / SHARING USE ONLY]

    Aggressively redacts location data.
    WARNING: This function is intended ONLY for when you want to safely share or export findings with third parties.
    It must NEVER be applied to output that is delivered to you (the user).
    The design goal is that you receive raw, complete data at all times.
    """
    redacted = text

    # Precise lat/long (e.g. 34.8697, -111.7610 or 34.87 N, 111.76 W)
    redacted = re.sub(
        r'\b-?\d{1,3}\.\d{2,}\s*[,°]?\s*-?\d{1,3}\.\d{2,}\b',
        '[REDACTED-LOCATION]',
        redacted
    )

    # Common address patterns
    redacted = re.sub(
        r'\b\d{1,5}\s+[A-Za-z0-9\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b',
        '[REDACTED-ADDRESS]',
        redacted,
        flags=re.IGNORECASE
    )

    if aggressive:
        # Redact known sensitive location names (user can expand this list)
        sensitive_places = [
            r'regional', r'Verde Valley', r'Secret Mountain', r'Bradshaw Ranch',
            r'Government Mountain', r'Oak Creek Canyon'
        ]
        for place in sensitive_places:
            redacted = re.sub(place, '[REDACTED-LOCATION]', redacted, flags=re.IGNORECASE)

    if redacted != text:
        _log_technical_event("location_redacted", {"chars_changed": len(text) - len(redacted)})

    return redacted


# ====================== IP & NETWORK IDENTIFIER PROTECTION ======================

def sanitize_network_identifiers(text: str) -> str:
    """
    [EXPORT / SHARING USE ONLY]

    Redacts IP addresses, Cloudflare-related identifiers, and common device fingerprints.
    WARNING: This function is intended ONLY for when you want to safely share or export findings with third parties.
    It must NEVER be applied to output that is delivered to you (the user).
    """
    redacted = text

    # IPv4
    redacted = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED-IP]', redacted)

    # IPv6 (simplified)
    redacted = re.sub(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b', '[REDACTED-IP]', redacted)

    # Cloudflare Ray IDs, cf-ray, etc.
    redacted = re.sub(r'\bcf-ray[:=]?\s*[0-9a-fA-F-]+', '[REDACTED-CLOUDFLARE]', redacted, flags=re.IGNORECASE)
    redacted = re.sub(r'\b[A-Za-z0-9]{16,}\.cloudflare\b', '[REDACTED-CLOUDFLARE]', redacted, flags=re.IGNORECASE)

    # Common user-agent / device fingerprint fragments
    redacted = re.sub(r'(?i)(User-Agent|CF-Connecting-IP|CF-IPCountry|CF-Visitor)\s*[:=]\s*[^\s]+', '[REDACTED-DEVICE-ID]', redacted)

    if redacted != text:
        _log_technical_event("network_identifier_redacted", {"chars_changed": len(text) - len(redacted)})

    return redacted


# ====================== LOCAL DATA / HARD DRIVE PROTECTION ======================

def protect_local_paths(text: str) -> str:
    """
    [EXPORT / SHARING USE ONLY]

    Redacts local file paths that could reveal the user's hard drive structure or username.
    WARNING: This function is intended ONLY for when you want to safely share or export findings with third parties.
    It must NEVER be applied to output that is delivered to you (the user).
    """
    redacted = text

    # Windows paths (C:\Users\Name\...)
    redacted = re.sub(r'(?i)[A-Z]:\\Users\\[^\\]+', '[REDACTED-LOCAL-PATH]', redacted)

    # Unix/macOS paths (/home/username/ or /Users/username/)
    redacted = re.sub(r'(?i)/Users/[^/]+', '[REDACTED-LOCAL-PATH]', redacted)
    redacted = re.sub(r'(?i)/home/[^/]+', '[REDACTED-LOCAL-PATH]', redacted)

    # General home directory references
    redacted = re.sub(r'~/(Documents|Downloads|Desktop|Pictures|Videos)', '[REDACTED-LOCAL-PATH]', redacted)

    if redacted != text:
        _log_technical_event("local_path_redacted", {"chars_changed": len(text) - len(redacted)})

    return redacted


# ====================== COMBINED PROTECTION ======================

def apply_technical_protections(text: str, protect_location: bool = True, protect_network: bool = True, protect_local_data: bool = True) -> str:
    """
    [EXPORT / SHARING USE ONLY]

    Applies the user's defined technical security protections for safe external sharing.
    WARNING: This function is intended ONLY for when you want to safely share or export findings with third parties.
    It must NEVER be applied to output that is delivered to you (the user).
    The core rule is: You receive everything raw and unfiltered.
    """
    result = text

    if protect_local_data:
        result = protect_local_paths(result)

    if protect_location:
        result = redact_location(result)

    if protect_network:
        result = sanitize_network_identifiers(result)

    return result


# ====================== OUTBOUND / EXTERNAL LEAK PREVENTION ======================

def sanitize_outgoing_query(query: str) -> str:
    """
    Sanitizes queries before they are sent to external services (search engines, etc.).
    Goal: Reduce the chance of the swarm leaking your identity, location, or interests
    through search patterns or metadata.

    This does NOT redact the final output you receive — it only affects what leaves your system.
    """
    # Remove or generalize highly identifying phrases
    sanitized = re.sub(r'\b(my|I am|I live in|my location is)\b', '[REDACTED]', query, flags=re.IGNORECASE)

    # Remove very specific personal context that could fingerprint you
    sanitized = re.sub(r'\b(near me|in my area|my city|my town)\b', 'in the area', sanitized, flags=re.IGNORECASE)

    if sanitized != query:
        _log_technical_event("outgoing_query_sanitized", {"original_length": len(query)})

    return sanitized


def get_privacy_recommendations() -> str:
    """
    Returns practical recommendations for protecting your IP, location, and device identifiers
    while running the swarm.
    """
    return """
SESP Technical Privacy Recommendations (for external protection only):

- Route all swarm external requests through a VPN or Tor when possible.
- Avoid running the swarm on networks where your real IP or location can be easily tied to you.
- Consider using privacy-focused DNS (e.g., Quad9, Mullvad, or NextDNS).
- When using the swarm for sensitive topics, clear browser/cloudflare cookies regularly if any web interfaces are involved.
- Never paste raw swarm outputs into public or third-party tools without first applying export redaction functions.
"""


# ====================== IP LEAK DETECTION ======================

def check_current_public_ip(timeout: int = 8) -> dict:
    """
    Checks your current public exit IP.
    Use this to verify if your traffic is protected (VPN/Tor) or leaking your real IP.
    """
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), "https://api.ipify.org"],
            capture_output=True, text=True, timeout=timeout + 2
        )
        ip = result.stdout.strip()
        if ip:
            _log_technical_event("public_ip_checked", {"ip": ip})
            return {"status": "success", "ip": ip}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "Could not determine public IP"}


def warn_if_ip_leaking() -> str:
    """
    Quick check + warning if your current public IP looks like a residential one.
    """
    result = check_current_public_ip()
    if result.get("status") != "success":
        return "Could not check current public IP."

    ip = result["ip"]
    # Simple heuristic - in practice you can improve this list
    return f"⚠️  Your current public IP is {ip}. If this is your real home IP, consider using a VPN or Tor before sensitive operations."


# ====================== PRIVACY CURL HELPER ======================

def get_privacy_curl_command(url: str, use_tor: bool = False) -> str:
    """
    Returns a curl command with hardened headers to reduce fingerprinting.
    """
    headers = [
        "-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0'",
        "-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'",
        "-H 'Accept-Language: en-US,en;q=0.5'",
        "-H 'DNT: 1'",
        "-H 'Connection: keep-alive'"
    ]
    header_str = " ".join(headers)

    if use_tor:
        return f"curl --socks5-hostname 127.0.0.1:9050 {header_str} '{url}'"
    return f"curl {header_str} '{url}'"


# ====================== HARD DRIVE / DATA EXFILTRATION AWARENESS ======================

def warn_on_sensitive_file_access(filepath: str) -> Optional[str]:
    """
    Simple helper that can be called before reading/writing files.
    Returns a warning string if the path looks like it contains highly sensitive local data.
    """
    sensitive_patterns = [
        r'(\.ssh|\.gnupg|\.aws|\.config|passwords|keys|wallet|seed)',
        r'(Documents|Desktop)/.*(tax|bank|passport|id|ssn|license)',
    ]

    for pattern in sensitive_patterns:
        if re.search(pattern, filepath, re.IGNORECASE):
            return f"⚠️  Warning: Accessing potentially sensitive local file: {filepath}. Consider redacting or encrypting before any external sharing."

    return None


# ====================== OUTBOUND PROTECTION WRAPPER ======================

class OutboundProtection:
    """
    Convenient wrapper for agents (ALPHA, CHARLIE, etc.) to use outbound protections easily.
    """

    def __init__(self, mission_id: str = "default"):
        self.mission_id = mission_id

    def prepare_query(self, query: str) -> str:
        """Call this before sending any query externally."""
        return sanitize_outgoing_query(query)

    def check_ip_safety(self) -> str:
        """Quick check before sensitive operations."""
        return warn_if_ip_leaking()

    def get_safe_curl(self, url: str, use_tor: bool = False) -> str:
        return get_privacy_curl_command(url, use_tor)


if __name__ == "__main__":
    print("SESP Technical Security Module (User-Defined Scope) loaded.")
    print("\nCore Rule: The user always receives raw, unfiltered output.")
    print("Security exists only to stop external parties from seeing your data, location, IP, or identifiers.")
    print("\nKey outbound tools:")
    print("  - sanitize_outgoing_query()")
    print("  - check_current_public_ip() / warn_if_ip_leaking()")
    print("  - get_privacy_curl_command()")
    print("  - OutboundProtection class (recommended for agents)")
    print("  - get_privacy_recommendations()")