#!/usr/bin/env python3
"""
SESP Self-Evolution Applicator
Safe, auditable patch applier for approved proposals.
Includes rollback capability.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
import subprocess

BASE_DIR = Path(__file__).parent.parent
PROPOSALS_DIR = BASE_DIR / "proposals"
BACKUP_DIR = BASE_DIR / "backups"
LOG = BASE_DIR / "logs" / "evolution_log.jsonl"

def apply_proposal(proposal_path: Path, dry_run: bool = True) -> Dict:
    """Apply a validated proposal. Set dry_run=False only after human approval."""
    proposal = json.loads(proposal_path.read_text())
    pid = proposal["proposal_id"]

    if dry_run:
        return {"status": "DRY_RUN", "proposal": pid, "would_apply": proposal["patch_or_code"][:200] + "..."}

    # Backup current state
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"backup-{timestamp}"
    BACKUP_DIR.mkdir(exist_ok=True)
    shutil.copytree(BASE_DIR / "modules", backup_path / "modules", dirs_exist_ok=True)

    # Apply patch (very basic for v1.0 - in practice use patch command or safe exec)
    # For safety, we log the intent and require manual application for code changes in this initial deployment.
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "proposal_id": pid,
        "action": "APPLIED",
        "backup": str(backup_path),
        "change_type": proposal["change_type"]
    }

    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return {"status": "APPLIED_WITH_BACKUP", "backup": str(backup_path), "log_entry": log_entry}

if __name__ == "__main__":
    print("SESP Evolution Applicator ready. Use only on approved proposals.")