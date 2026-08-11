"""
Signal 04 — EHV Load-Balance proxy (EIA real data for AZPS balancing authority)
Uses the official EIA v2 API (hourly demand / interchange).
Requires free API key (EIA_API_KEY env or data/eia_key.txt).
"""
from datetime import datetime, timedelta

from .base import RealIngestor, IngestorError, get_eia_key
from ..models import TelemetryPoint


class EIAGridIngestor(RealIngestor):
    signal_id = 4
    name = "AZPS Balancing Authority Load (EIA)"
    source_type = "proxy"   # aggregated BA-level, not per-line SCADA

    RESPONDENT = "AZPS"
    SERIES_TYPE = "D"       # demand (actual)

    def fetch(self, start: datetime, end: datetime) -> list[TelemetryPoint]:
        key = get_eia_key()
        if not key:
            raise IngestorError(
                "No EIA API key found. Set EIA_API_KEY env var or place key in data/eia_key.txt"
            )

        url = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
        params = {
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": self.RESPONDENT,
            "facets[type][]": self.SERIES_TYPE,
            "start": start.strftime("%Y-%m-%dT%H"),
            "end": end.strftime("%Y-%m-%dT%H"),
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 5000,
            "api_key": key,
        }

        try:
            resp = self.client.get(url, params=params)
            if resp.status_code == 401:
                raise IngestorError("EIA rejected key (401). Check EIA_API_KEY.")
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise IngestorError(f"EIA API error: {exc}") from exc

        points: list[TelemetryPoint] = []
        for row in data.get("response", {}).get("data", []):
            try:
                # period is like "2025-05-28T17"
                dt = datetime.fromisoformat(row["period"]).replace(tzinfo=__import__("datetime").timezone.utc)
                val = float(row["value"])
                points.append(
                    TelemetryPoint(
                        ts=dt,
                        signal_id=self.signal_id,
                        value=val,
                        unit="MW",
                        source="proxy",
                        metadata={
                            "respondent": self.RESPONDENT,
                            "series": "demand",
                            "period_raw": row["period"],
                            "source": "EIA Form 930 / RTO",
                        },
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue

        points.sort(key=lambda p: p.ts)
        return points
