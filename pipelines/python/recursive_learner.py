#!/usr/bin/env python3
"""
Recursive Learning Module

Enables a predictive system to improve from its own prediction → outcome cycles.

Core loop:
1. Make a prediction for a future period using current model parameters.
2. When actual data arrives, log (prediction, actual, error, context).
3. Use accumulated history to recursively update / improve model parameters.
4. Future predictions use the refined parameters.
5. Track performance improvement over successive update cycles.

This creates a closed self-improvement loop suitable for environments where
ground truth arrives with lag.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ============================================================
# PATHS & DEFAULTS
# ============================================================

BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / "state" / "learned_model_state.json"

BASE_COEFFS = {
    "intercept": 1.8,
    "beta_unemp": 0.55,
    "beta_mort_rate": 0.22,
    "beta_hpa": -0.12
}

DEFAULT_STATE = {
    "version": "1.0",
    "last_updated": None,
    "base_coefficients": BASE_COEFFS.copy(),
    "learned_coefficients": BASE_COEFFS.copy(),
    "prediction_log": [],
    "performance_metrics": {
        "total_predictions": 0,
        "mae": None,
        "recent_mae_trend": [],
        "improvement_vs_base": None
    },
    "learning_notes": []
}


def _load_state() -> Dict:
    """Load persistent learning state or initialize if missing."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        for k, v in DEFAULT_STATE.items():
            if k not in state:
                state[k] = v
        return state
    else:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(DEFAULT_STATE, f, indent=2)
        return DEFAULT_STATE.copy()


def _save_state(state: Dict):
    """Persist the current learning state."""
    state["last_updated"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def predict_with_current_model(
    unemp: float,
    mort_rate: float,
    hpa_yoy: float,
    use_learned: bool = True
) -> float:
    """Make a prediction using either base or the latest learned coefficients."""
    state = _load_state()
    coeffs = state["learned_coefficients"] if use_learned else state["base_coefficients"]

    pred = (
        coeffs["intercept"]
        + coeffs["beta_unemp"] * unemp
        + coeffs["beta_mort_rate"] * mort_rate
        + coeffs["beta_hpa"] * hpa_yoy
    )
    return round(pred, 3)


def log_prediction_outcome(
    period: str,
    predicted: float,
    actual: float,
    inputs: Dict,
    scenario: str = "base",
    notes: str = ""
) -> Dict:
    """Log a prediction and its eventual actual outcome — the key step for recursive learning."""
    state = _load_state()

    error = round(actual - predicted, 3)
    abs_error = abs(error)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "period": period,
        "predicted": predicted,
        "actual": actual,
        "error": error,
        "abs_error": abs_error,
        "inputs": inputs,
        "scenario": scenario,
        "notes": notes
    }

    state["prediction_log"].append(entry)
    state["performance_metrics"]["total_predictions"] = len(state["prediction_log"])

    errors = [e["abs_error"] for e in state["prediction_log"]]
    state["performance_metrics"]["mae"] = round(np.mean(errors), 3)

    recent = errors[-5:]
    state["performance_metrics"]["recent_mae_trend"] = [round(e, 3) for e in recent]

    _save_state(state)
    return entry


def update_learned_model(method: str = "re_fit") -> Dict:
    """
    Recursively update model coefficients based on logged outcomes.

    Methods:
    - "re_fit": Re-estimate coefficients using all logged (inputs → actual) pairs (OLS).
    - "incremental": Small gradient-style adjustment toward reducing recent errors.
    """
    state = _load_state()
    log = state["prediction_log"]

    if len(log) < 3:
        note = "Not enough data points (<3) for meaningful recursive update."
        state["learning_notes"].append(note)
        _save_state(state)
        return {"status": "insufficient_data", "note": note}

    X = []
    y = []
    for entry in log:
        inp = entry["inputs"]
        if all(k in inp for k in ["unemp", "mort_rate", "hpa_yoy"]):
            X.append([1.0, inp["unemp"], inp["mort_rate"], inp["hpa_yoy"]])
            y.append(entry["actual"])

    if len(X) < 3:
        note = "Insufficient complete input records for update."
        state["learning_notes"].append(note)
        _save_state(state)
        return {"status": "insufficient_data", "note": note}

    X = np.array(X)
    y = np.array(y)

    if method == "re_fit":
        try:
            coeffs, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
            new_intercept, new_beta_unemp, new_beta_mort, new_beta_hpa = coeffs

            # Gentle blend to prevent wild swings
            old = state["learned_coefficients"]
            blend = 0.7
            state["learned_coefficients"] = {
                "intercept": round(blend * new_intercept + (1 - blend) * old["intercept"], 4),
                "beta_unemp": round(blend * new_beta_unemp + (1 - blend) * old["beta_unemp"], 4),
                "beta_mort_rate": round(blend * new_beta_mort + (1 - blend) * old["beta_mort_rate"], 4),
                "beta_hpa": round(blend * new_beta_hpa + (1 - blend) * old["beta_hpa"], 4)
            }

            base_preds = [
                state["base_coefficients"]["intercept"]
                + state["base_coefficients"]["beta_unemp"] * e["inputs"]["unemp"]
                + state["base_coefficients"]["beta_mort_rate"] * e["inputs"]["mort_rate"]
                + state["base_coefficients"]["beta_hpa"] * e["inputs"]["hpa_yoy"]
                for e in log if all(k in e["inputs"] for k in ["unemp", "mort_rate", "hpa_yoy"])
            ]
            base_mae = np.mean([abs(a - p) for a, p in zip(y, base_preds)]) if base_preds else None
            learned_mae = state["performance_metrics"]["mae"]

            if base_mae and learned_mae:
                improvement = round((base_mae - learned_mae) / base_mae * 100, 1)
                state["performance_metrics"]["improvement_vs_base"] = f"{improvement}% better MAE"

            note = f"Model recursively updated via re-fit on {len(log)} logged outcomes. Blended 70/30."
            state["learning_notes"].append(note)

        except Exception as e:
            note = f"Re-fit failed: {str(e)}"
            state["learning_notes"].append(note)

    elif method == "incremental":
        recent = log[-1]
        error = recent["error"]
        inp = recent["inputs"]
        lr = 0.01

        lc = state["learned_coefficients"]
        lc["intercept"] += lr * error
        lc["beta_unemp"] += lr * error * inp.get("unemp", 0)
        lc["beta_mort_rate"] += lr * error * inp.get("mort_rate", 0)
        lc["beta_hpa"] += lr * error * inp.get("hpa_yoy", 0)

        for k in lc:
            lc[k] = round(lc[k], 4)

        note = f"Incremental update applied based on latest error ({error}). Learning rate {lr}."
        state["learning_notes"].append(note)

    _save_state(state)
    return {
        "status": "updated",
        "method": method,
        "new_coefficients": state["learned_coefficients"],
        "note": note,
        "total_logged_outcomes": len(log)
    }


def get_learning_status() -> Dict:
    """Return current state of recursive learning."""
    state = _load_state()
    return {
        "last_updated": state.get("last_updated"),
        "total_logged_outcomes": len(state["prediction_log"]),
        "current_mae": state["performance_metrics"].get("mae"),
        "improvement_vs_base": state["performance_metrics"].get("improvement_vs_base"),
        "learned_coefficients": state["learned_coefficients"],
        "base_coefficients": state["base_coefficients"],
        "recent_notes": state["learning_notes"][-3:] if state["learning_notes"] else []
    }


def reset_learning(confirm: bool = False):
    """Reset learned state back to base model."""
    if not confirm:
        return {"status": "aborted", "message": "Pass confirm=True to reset."}
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    return {"status": "reset", "message": "Learning state reset to base model."}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Recursive Learning CLI")
    sub = parser.add_subparsers(dest="command")

    p_log = sub.add_parser("log", help="Log a prediction outcome")
    p_log.add_argument("--period", required=True)
    p_log.add_argument("--predicted", type=float, required=True)
    p_log.add_argument("--actual", type=float, required=True)
    p_log.add_argument("--unemp", type=float, required=True)
    p_log.add_argument("--mort_rate", type=float, required=True)
    p_log.add_argument("--hpa_yoy", type=float, required=True)
    p_log.add_argument("--scenario", default="base")

    p_update = sub.add_parser("update", help="Trigger recursive model update")
    p_update.add_argument("--method", choices=["re_fit", "incremental"], default="re_fit")

    p_status = sub.add_parser("status", help="Show current learning status")

    args = parser.parse_args()

    if args.command == "log":
        result = log_prediction_outcome(
            period=args.period,
            predicted=args.predicted,
            actual=args.actual,
            inputs={"unemp": args.unemp, "mort_rate": args.mort_rate, "hpa_yoy": args.hpa_yoy},
            scenario=args.scenario
        )
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "update":
        result = update_learned_model(method=args.method)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "status":
        print(json.dumps(get_learning_status(), indent=2, default=str))

    else:
        print("Usage: recursive_learner.py {log|update|status}")
        print("Example: python recursive_learner.py log --period Q2_2026 --predicted 5.1 --actual 4.8 --unemp 4.3 --mort_rate 6.7 --hpa_yoy 3.8")
        print("         python recursive_learner.py update --method re_fit")
        print("         python recursive_learner.py status")
