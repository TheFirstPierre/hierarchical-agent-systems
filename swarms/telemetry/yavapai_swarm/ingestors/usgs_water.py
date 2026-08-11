"""
Signal 05 — Verde Watershed Flow (real USGS NWIS data)
"""
from datetime import datetime
from typing import Any

from .base import RealIngestor, IngestorError, window_from_spec
from ..models import TelemetryPoint
from ..config import SIGNALS


class USGSWaterIngestor(RealIngestor):
    signal_id = 5
    name = "Verde River Flow (USGS NWIS)"
    source_type = "real"

    # Good representative gauge for the middle Verde in Yavapai area
    # 09510000 = Verde River near Camp Verde, AZ (active, long record)
    DEFAULT_SITE = "09510000"
    PARAM = "00060"  # Discharge, cubic feet per second

    def __init__(self, site: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.site = site or self.DEFAULT_SITE

    def fetch(self, start: datetime, end: datetime) -> list[TelemetryPoint]:
        url = "https://waterservices.usgs.gov/nwis/iv/"
        params = {
            "format": "json",
            "sites": self.site,
            "parameterCd": self.PARAM,
            "startDT": start.isoformat(),
            "endDT": end.isoformat(),
        }

        try:
            resp = self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise IngestorError(f"USGS NWIS fetch failed: {exc}") from exc

        points: list[TelemetryPoint] = []

        try:
            ts = data["value"]["timeSeries"][0]["values"][0]["value"]
            for row in ts:
                # USGS returns value as string, dateTime in local with tz info
                dt = datetime.fromisoformat(row["dateTime"].replace("Z", "+00:00"))
                val = float(row["value"])
                points.append(
                    TelemetryPoint(
                        ts=dt,
                        signal_id=self.signal_id,
                        value=val,
                        unit="cfs",
                        source="real",
                        metadata={
                            "site": self.site,
                            "agency": "USGS",
                            "parameter": "discharge_cfs",
                            "raw_value": row["value"],
                        },
                    )
                )
        except (KeyError, IndexError, ValueError) as exc:
            raise IngestorError(f"Unexpected USGS response structure: {exc}") from exc

        points.sort(key=lambda p: p.ts)
        return points
