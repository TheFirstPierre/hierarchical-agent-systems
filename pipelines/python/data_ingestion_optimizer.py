#!/usr/bin/env python3
"""
Data Ingestion & Token Optimization Module

Purpose:
- Ingest large tabular datasets (CSV, Excel, Parquet) efficiently.
- Perform multi-layer summarization to extract maximum signal with minimal tokens.
- Support time-series regime detection, tier classification, anomaly flagging.
- Generate compact structured outputs (JSON + human-readable brief) optimized for LLM / agent context windows.
- Prepare enriched features for downstream predictive models or multi-agent systems.

This pattern enables handling years of high-frequency data without exhausting context limits
while preserving the information that actually drives decisions.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

try:
    import pyarrow  # noqa: F401
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False

# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_MATRIX_THRESHOLDS = {
    "mortgage_delinq": {"green": 3.0, "yellow_upper": 6.0, "red": 7.0},
    # Extend for other systemic indicators as needed
}

# ============================================================
# CORE FUNCTIONS
# ============================================================

def detect_file_type(file_path: Union[str, Path]) -> str:
    """Auto-detect file type from extension."""
    suffix = Path(file_path).suffix.lower()
    if suffix in [".csv", ".txt"]:
        return "csv"
    elif suffix in [".xlsx", ".xls"]:
        return "excel"
    elif suffix in [".parquet", ".pq"]:
        return "parquet"
    else:
        return "csv"


def load_large_dataset(
    file_path: Union[str, Path],
    file_type: str = "auto",
    chunksize: int = 100_000,
    usecols: Optional[List[str]] = None,
    parse_dates: Optional[List[str]] = None,
    dtype: Optional[Dict] = None,
    low_memory: bool = False,
) -> pd.DataFrame:
    """
    Efficiently load very large datasets using chunking where beneficial.
    Returns a single concatenated DataFrame.
    """
    file_type = file_type if file_type != "auto" else detect_file_type(file_path)
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    print(f"[INFO] Loading {file_type.upper()} file: {file_path} (chunk size: {chunksize:,})")

    if file_type == "parquet":
        df = pd.read_parquet(file_path, columns=usecols)
        if parse_dates:
            for col in parse_dates:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    elif file_type == "excel":
        df = pd.read_excel(file_path, usecols=usecols, parse_dates=parse_dates, dtype=dtype)
        return df

    else:  # CSV
        chunks = []
        try:
            reader = pd.read_csv(
                file_path,
                usecols=usecols,
                parse_dates=parse_dates,
                dtype=dtype,
                chunksize=chunksize,
                low_memory=low_memory,
                engine="pyarrow" if HAS_PYARROW else "c",
            )
            for i, chunk in enumerate(reader):
                chunks.append(chunk)
                if (i + 1) % 5 == 0:
                    print(f"  ... loaded {(i+1)*chunksize:,} rows")
            df = pd.concat(chunks, ignore_index=True)
            print(f"[INFO] Total rows loaded: {len(df):,}")
            return df
        except Exception as e:
            print(f"[WARN] Chunked read failed ({e}). Falling back to full read...")
            return pd.read_csv(file_path, usecols=usecols, parse_dates=parse_dates, dtype=dtype)


def classify_matrix_tier(
    value: float,
    thresholds: Dict[str, float] = None
) -> str:
    """Classify a value into Green / Yellow / Red risk tiers."""
    if thresholds is None:
        thresholds = DEFAULT_MATRIX_THRESHOLDS["mortgage_delinq"]
    if value < thresholds["green"]:
        return "Green"
    elif value <= thresholds["yellow_upper"]:
        return "Yellow"
    else:
        return "Red"


def detect_regimes(
    df: pd.DataFrame,
    time_col: str,
    value_col: str,
    min_regime_length: int = 3,
    change_threshold: float = 0.5
) -> List[Dict]:
    """Simple regime detection based on significant level shifts."""
    if time_col not in df.columns or value_col not in df.columns:
        return []

    df_sorted = df.sort_values(time_col).reset_index(drop=True)
    series = df_sorted[value_col].dropna()

    if len(series) < min_regime_length * 2:
        return []

    rolling_mean = series.rolling(window=min_regime_length, min_periods=1).mean()
    diff = rolling_mean.diff().abs()
    regime_changes = diff[diff > change_threshold].index.tolist()

    regimes = []
    start_idx = 0
    for change_idx in regime_changes + [len(series)]:
        if change_idx - start_idx >= min_regime_length:
            segment = series.iloc[start_idx:change_idx]
            regimes.append({
                "start": str(df_sorted.loc[segment.index[0], time_col]),
                "end": str(df_sorted.loc[segment.index[-1], time_col]),
                "mean": round(float(segment.mean()), 3),
                "std": round(float(segment.std()), 3),
                "min": round(float(segment.min()), 3),
                "max": round(float(segment.max()), 3),
                "length": len(segment)
            })
        start_idx = change_idx

    return regimes


def compute_compact_summary(
    df: pd.DataFrame,
    time_col: Optional[str] = None,
    value_cols: Optional[List[str]] = None,
    group_by: Optional[str] = None,
    matrix_col: Optional[str] = None,
    apply_matrix: bool = True
) -> Dict:
    """Generate a highly compressed yet information-rich summary (token optimization core)."""
    summary = {
        "generated_at": datetime.now().isoformat(),
        "row_count": len(df),
        "column_count": len(df.columns),
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024**2), 2),
        "overall_stats": {},
        "trends": {},
        "regimes": {},
        "anomalies": {},
        "matrix_tiers": {},
        "recommendations": []
    }

    if value_cols is None:
        value_cols = df.select_dtypes(include=[np.number]).columns.tolist()[:10]

    for col in value_cols:
        if col in df.columns:
            s = df[col].dropna()
            if len(s) > 0:
                summary["overall_stats"][col] = {
                    "mean": round(float(s.mean()), 4),
                    "median": round(float(s.median()), 4),
                    "std": round(float(s.std()), 4),
                    "min": round(float(s.min()), 4),
                    "max": round(float(s.max()), 4),
                    "latest": round(float(s.iloc[-1]), 4) if len(s) > 0 else None,
                }

    if time_col and time_col in df.columns:
        for col in value_cols:
            if col in df.columns:
                try:
                    df_temp = df[[time_col, col]].dropna()
                    if len(df_temp) > 2:
                        df_temp["_t"] = pd.to_datetime(df_temp[time_col]).astype(np.int64) / 1e9
                        slope = np.polyfit(df_temp["_t"], df_temp[col], 1)[0]
                        summary["trends"][col] = {
                            "direction": "rising" if slope > 0 else "falling" if slope < 0 else "flat",
                            "slope_per_sec": round(float(slope), 8)
                        }
                except Exception:
                    pass

    if time_col and value_cols:
        for col in value_cols[:3]:
            regimes = detect_regimes(df, time_col, col)
            if regimes:
                summary["regimes"][col] = regimes

    for col in value_cols:
        if col in df.columns:
            s = df[col].dropna()
            if len(s) > 10:
                q1, q3 = s.quantile([0.25, 0.75])
                iqr = q3 - q1
                outliers = s[(s < (q1 - 1.5 * iqr)) | (s > (q3 + 1.5 * iqr))]
                if len(outliers) > 0:
                    summary["anomalies"][col] = {
                        "count": len(outliers),
                        "pct": round(len(outliers) / len(s) * 100, 2),
                        "extreme_values": [round(float(v), 3) for v in outliers.nlargest(3).tolist()]
                    }

    if apply_matrix and (matrix_col in df.columns if matrix_col else True):
        tier_col = matrix_col or (value_cols[0] if value_cols else None)
        if tier_col and tier_col in df.columns:
            tiers = df[tier_col].dropna().apply(classify_matrix_tier)
            tier_counts = tiers.value_counts().to_dict()
            summary["matrix_tiers"] = {
                "distribution": {k: int(v) for k, v in tier_counts.items()},
                "latest_tier": classify_matrix_tier(df[tier_col].iloc[-1]) if len(df) > 0 else "Unknown",
                "time_in_yellow_red": int((tiers != "Green").sum()) if len(tiers) > 0 else 0
            }

    recs = []
    if summary.get("matrix_tiers", {}).get("latest_tier") == "Yellow":
        recs.append("System in Elevated (Yellow) tier — monitor for drift toward Red.")
    if summary.get("anomalies"):
        recs.append("Anomalies detected — investigate outlier periods.")
    if summary.get("trends"):
        rising = [k for k, v in summary["trends"].items() if v.get("direction") == "rising"]
        if rising:
            recs.append(f"Rising trend detected in: {', '.join(rising[:3])}.")
    summary["recommendations"] = recs[:5]

    return summary


def generate_token_optimized_brief(summary: Dict, max_sections: int = 6) -> str:
    """Convert compact summary into a highly token-efficient textual brief."""
    lines = []
    lines.append("=== TOKEN-OPTIMIZED DATA BRIEF ===")
    lines.append(f"Rows: {summary['row_count']:,} | Generated: {summary['generated_at'][:19]}")

    if summary.get("overall_stats"):
        lines.append("\n[OVERALL STATS]")
        for col, stats in list(summary["overall_stats"].items())[:4]:
            lines.append(f"  {col}: mean={stats['mean']}, latest={stats['latest']}, range=[{stats['min']}, {stats['max']}]")

    if summary.get("matrix_tiers"):
        mt = summary["matrix_tiers"]
        lines.append(f"\n[MATRIX TIER DISTRIBUTION] Latest: {mt.get('latest_tier', 'N/A')}")
        lines.append(f"  {mt.get('distribution', {})} | Time in Yellow/Red: {mt.get('time_in_yellow_red', 0)} periods")

    if summary.get("trends"):
        lines.append("\n[TRENDS]")
        for col, t in list(summary["trends"].items())[:3]:
            lines.append(f"  {col}: {t['direction']} (slope {t['slope_per_sec']:.2e})")

    if summary.get("regimes"):
        lines.append("\n[REGIMES DETECTED]")
        for col, regs in list(summary["regimes"].items())[:2]:
            for r in regs[:2]:
                lines.append(f"  {col} {r['start']}→{r['end']}: mean={r['mean']}")

    if summary.get("anomalies"):
        lines.append("\n[ANOMALIES]")
        for col, a in list(summary["anomalies"].items())[:2]:
            lines.append(f"  {col}: {a['count']} outliers ({a['pct']}%)")

    if summary.get("recommendations"):
        lines.append("\n[RECOMMENDATIONS]")
        for r in summary["recommendations"]:
            lines.append(f"  • {r}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Data Ingestion & Token Optimization Tool"
    )
    parser.add_argument("file_path", help="Path to large data file (CSV, Excel, Parquet)")
    parser.add_argument("--file-type", default="auto", choices=["auto", "csv", "excel", "parquet"])
    parser.add_argument("--time-col", default=None, help="Name of datetime column for trends/regimes")
    parser.add_argument("--value-cols", nargs="+", default=None, help="Numeric columns to analyze")
    parser.add_argument("--matrix-col", default=None, help="Column for risk-tier classification")
    parser.add_argument("--output-json", default=None, help="Path to save full JSON summary")
    parser.add_argument("--output-brief", default=None, help="Path to save token-optimized text brief")
    parser.add_argument("--chunksize", type=int, default=100000, help="Chunk size for large CSV reads")

    args = parser.parse_args()

    try:
        df = load_large_dataset(
            args.file_path,
            file_type=args.file_type,
            chunksize=args.chunksize,
            parse_dates=[args.time_col] if args.time_col else None
        )

        summary = compute_compact_summary(
            df,
            time_col=args.time_col,
            value_cols=args.value_cols,
            matrix_col=args.matrix_col,
            apply_matrix=True
        )

        brief = generate_token_optimized_brief(summary)

        print("\n" + "="*70)
        print(brief)
        print("="*70)

        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"\n[INFO] Full JSON summary saved to: {args.output_json}")

        if args.output_brief:
            with open(args.output_brief, "w") as f:
                f.write(brief)
            print(f"[INFO] Token-optimized brief saved to: {args.output_brief}")

        print("\n[COMPACT JSON FOR LLM / AGENT INPUT]")
        print(json.dumps({
            "row_count": summary["row_count"],
            "latest_stats": summary.get("overall_stats", {}),
            "matrix_tiers": summary.get("matrix_tiers", {}),
            "key_trends": summary.get("trends", {}),
            "recommendations": summary.get("recommendations", [])
        }, indent=2, default=str))

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
