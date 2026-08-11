#!/usr/bin/env python3
"""
TELEMETRY_SWARM_V5 — The Expanded Yavapai 13-Signal Swarm

One-command runner (modeled on glass-x patterns).

Usage:
    python run.py                 # Launches the beautiful live glassmorphism dashboard
    python run.py --cli           # Drops to CLI (activate, scenarios, etc.)
    python -m yavapai_swarm ...   # Direct CLI access

This will:
- Create .venv if missing
- Install dependencies
- Start the live swarm monitor on http://127.0.0.1:8080
"""

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"
BIN = VENV / ("Scripts" if os.name == "nt" else "bin")
DATA_DIR = ROOT / "data"

def main():
    print("🛰️  TELEMETRY_SWARM_V5 — Expanded Yavapai 13-Signal Swarm")
    print("    4 Agents • 13 Signals • Cross-Domain Collision Detection\n")

    # Create venv if needed
    if not VENV.exists():
        print("Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])

    python = BIN / ("python.exe" if os.name == "nt" else "python")
    pip = BIN / ("pip.exe" if os.name == "nt" else "pip")

    # Install requirements
    print("Installing dependencies (first run can take 45-90s)...")
    subprocess.check_call([str(pip), "install", "-r", str(ROOT / "requirements.txt"), "--quiet"])

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check if user wants pure CLI mode
    if "--cli" in sys.argv:
        print("\n✅ Environment ready. Launching CLI...\n")
        os.chdir(ROOT)
        os.execv(str(python), [str(python), "-m", "yavapai_swarm", "--help"])
        return

    print("\n✅ Starting Yavapai Swarm Dashboard")
    print("   Open http://127.0.0.1:8080 in your browser")
    print("   (Live updating agents + coupled anomalies + one-click JSON export)\n")

    os.chdir(ROOT)
    os.execv(
        str(python),
        [
            str(python),
            "-m",
            "uvicorn",
            "yavapai_swarm.dashboard:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
            "--reload",
        ],
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Yavapai Swarm deactivated.")
