"""
Pydantic models for TELEMETRY_SWARM_V5
The canonical schema for the required JSON output (prioritizing Coupled Anomalies).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Any
from pydantic import BaseModel, Field


class TelemetryPoint(BaseModel):
    ts: datetime
    signal_id: int
    value: float
    unit: str
    source: Literal["real", "proxy", "synthetic"] = "synthetic"
    metadata: dict[str, Any] = Field(default_factory=dict)


class Anomaly(BaseModel):
    signal_id: int
    ts: datetime
    severity: float = Field(ge=0.0, le=1.0)
    detector: str
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class CoupledAnomaly(BaseModel):
    coupling_id: str
    involved_clusters: list[str]
    signals: list[int]
    severity: float = Field(ge=0.0, le=1.0)
    first_seen: datetime
    last_seen: datetime
    hypothesis: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    cross_check: str | None = None


class SwarmReport(BaseModel):
    """The primary deliverable JSON. Prioritizes coupled_anomalies as requested."""

    schema_version: str = "5.0"
    activation: str = "TELEMETRY_SWARM_V5"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: str = "EXPERT"
    window: dict[str, datetime | str] = Field(default_factory=dict)

    agents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    coupled_anomalies: list[CoupledAnomaly] = Field(default_factory=list)
    per_cluster_anomalies: dict[str, list[Anomaly]] = Field(default_factory=dict)
    cross_checks_performed: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    data_sources: dict[str, str] = Field(default_factory=dict)
    real_data_summary: dict[str, Any] | None = None
    real_telemetry: dict[str, list[dict]] | None = None   # raw points when --real was used

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


# Convenience for future use
SignalCluster = Literal["ECHO", "TESSA", "CYBER", "VECTOR"]
