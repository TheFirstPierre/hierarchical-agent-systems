#!/usr/bin/env python3
"""
Illustrative Mortgage Delinquency Prediction Model

Educational / quick-scenario tool for systemic risk sensitivity analysis.
Always prioritize official MBA National Delinquency Survey and ICE First Look data
for real decisions.
"""

import argparse
import sys
from datetime import datetime

# Model coefficients (illustrative linear specification)
INTERCEPT = 1.8
BETA_UNEMP = 0.55
BETA_MORT_RATE = 0.22
BETA_HPA = -0.12

BASE_SERIOUS_RATIO = 0.46

SCENARIOS = {
    "base": {
        "unemp": 4.3,
        "mort_rate": 6.8,
        "hpa_yoy": 3.5,
        "description": "Base case: stable labor market, normalized rates, moderate home price growth"
    },
    "optimistic": {
        "unemp": 3.8,
        "mort_rate": 5.8,
        "hpa_yoy": 5.0,
        "description": "Optimistic: strong employment, rate relief, robust HPA"
    },
    "stress": {
        "unemp": 5.5,
        "mort_rate": 7.5,
        "hpa_yoy": 0.5,
        "description": "Stress: rising unemployment, higher for longer rates, flat HPA"
    },
    "severe": {
        "unemp": 7.0,
        "mort_rate": 8.5,
        "hpa_yoy": -2.0,
        "description": "Severe: recessionary unemployment spike, elevated rates, declining home prices"
    }
}

def predict_total_delinq(unemp: float, mort_rate: float, hpa_yoy: float) -> float:
    """Predict total delinquency rate (30+ DPD, seasonally adjusted %)."""
    return INTERCEPT + BETA_UNEMP * unemp + BETA_MORT_RATE * mort_rate + BETA_HPA * hpa_yoy

def estimate_serious_delinq(total_delinq: float, scenario: str = "base") -> float:
    """Estimate serious delinquency (90+ DPD or foreclosure)."""
    ratio = BASE_SERIOUS_RATIO
    if scenario in ["stress", "severe"]:
        multiplier = 1.15 if scenario == "stress" else 1.25
        ratio = min(ratio * multiplier, 0.65)
    return total_delinq * ratio

def main():
    parser = argparse.ArgumentParser(
        description="Illustrative US Mortgage Delinquency Predictor (educational use only)",
        epilog="IMPORTANT: This is NOT an official forecast. Use MBA/ICE data for real decisions."
    )
    parser.add_argument("--unemp", type=float, help="Unemployment rate (%)")
    parser.add_argument("--mort_rate", type=float, help="30-year fixed mortgage rate (%)")
    parser.add_argument("--hpa_yoy", type=float, help="Home price appreciation YoY (%)")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default=None,
                        help="Named scenario (overrides individual flags if provided)")
    parser.add_argument("--serious", action="store_true",
                        help="Also output estimated serious delinquency rate")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()

    if args.scenario:
        params = SCENARIOS[args.scenario]
        unemp = params["unemp"]
        mort_rate = params["mort_rate"]
        hpa_yoy = params["hpa_yoy"]
        scenario_name = args.scenario
        scenario_desc = params["description"]
    else:
        if args.unemp is None or args.mort_rate is None or args.hpa_yoy is None:
            print("Error: Provide --unemp, --mort_rate, and --hpa_yoy OR use --scenario", file=sys.stderr)
            parser.print_help()
            sys.exit(1)
        unemp = args.unemp
        mort_rate = args.mort_rate
        hpa_yoy = args.hpa_yoy
        scenario_name = "custom"
        scenario_desc = "Custom inputs provided via CLI"

    total_pred = predict_total_delinq(unemp, mort_rate, hpa_yoy)
    serious_pred = estimate_serious_delinq(total_pred, scenario_name) if args.serious or args.scenario else None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if args.json:
        import json
        output = {
            "timestamp": timestamp,
            "scenario": scenario_name,
            "inputs": {
                "unemployment_rate_pct": unemp,
                "30yr_mortgage_rate_pct": mort_rate,
                "hpa_yoy_pct": hpa_yoy
            },
            "predictions": {
                "total_delinq_30plus_pct": round(total_pred, 2),
            },
            "disclaimer": "EDUCATIONAL/ILLUSTRATIVE ONLY. Not a substitute for official MBA or ICE data."
        }
        if serious_pred is not None:
            output["predictions"]["serious_delinq_90plus_est_pct"] = round(serious_pred, 2)
        print(json.dumps(output, indent=2))
    else:
        print("=" * 70)
        print("MORTGAGE DEFAULT PREDICTOR — ILLUSTRATIVE MODEL")
        print(f"Run time: {timestamp}")
        print("=" * 70)
        print(f"\nScenario: {scenario_name.upper()}")
        print(f"Description: {scenario_desc}")
        print("\nInputs:")
        print(f"  Unemployment Rate:     {unemp:.1f}%")
        print(f"  30-Year Mortgage Rate: {mort_rate:.1f}%")
        print(f"  Home Price Apprec. YoY: {hpa_yoy:.1f}%")
        print("\nPredictions (Illustrative Linear Model):")
        print(f"  Total Delinquency (30+ DPD): {total_pred:.2f}%")
        if serious_pred is not None:
            print(f"  Serious Delinquency (est. 90+/FC): {serious_pred:.2f}%")
        print("\n" + "-" * 70)
        print("MODEL FORMULA:")
        print("  Total Delinq % ≈ 1.8 + 0.55×Unemp + 0.22×MortRate − 0.12×HPA_YoY")
        print("-" * 70)
        print("\n⚠️  DISCLAIMER:")
        print("This is an EDUCATIONAL and QUICK-SCENARIO tool only.")
        print("It is NOT calibrated for tails and ignores many real-world factors.")
        print("ALWAYS use official sources for decisions:")
        print("  • MBA National Delinquency Survey")
        print("  • ICE Mortgage Technology First Look")
        print("  • FRED, FHFA, BLS, Freddie Mac PMMS")

if __name__ == "__main__":
    main()
