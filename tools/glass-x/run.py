#!/usr/bin/env python3
"""
Project Glass X - One-command runner

Usage:
    python run.py

This will:
- Create venv if missing
- Install dependencies
- Start the app on http://localhost:8000
"""

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"
BIN = VENV / ("Scripts" if os.name == "nt" else "bin")

def main():
    print("🚀 Project Glass X")

    # Create venv if needed
    if not VENV.exists():
        print("Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])

    python = BIN / ("python.exe" if os.name == "nt" else "python")
    pip = BIN / ("pip.exe" if os.name == "nt" else "pip")

    # Install requirements
    print("Installing dependencies (first run can take 30-60s)...")
    subprocess.check_call([str(pip), "install", "-r", "requirements.txt", "--quiet"])

    # Ensure data dir exists
    (ROOT / "data").mkdir(exist_ok=True)

    print("\n✅ Starting Project Glass X")
    print("   Open http://localhost:8000 in your browser\n")

    # Run uvicorn
    os.chdir(ROOT)
    os.execv(str(python), [str(python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Glass X stopped.")
