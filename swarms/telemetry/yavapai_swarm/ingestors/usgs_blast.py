"""
Signal 07 — Industrial Blasting (Drake Cement + Jerome area)
Real data from USGS FDSN Event API, filtered to quarry blast / explosion.
"""
from datetime import datetime

from .base import RealIngestor, IngestorError
from ..models import TelemetryPoint


class USGSBlastIngestor(RealIngestor):
    signal_id = 7
    name = "Quarry Blasts (USGS FDSN)"
    source_type = "real"

    # Drake Cement (Paulden) + Jerome area
    LAT = 34.85
    LON = -112.35
    MAX_RADIUS_KM = 55

    def fetch(self, start: datetime, end: datetime) -> list[TelemetryPoint]:
        url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        params = {
            "format": "geojson",
            "starttime": start.isoformat(),
            "endtime": end.isoformat(),
            "latitude": self.LAT,
            "longitude": self.LON,
            "maxradiuskm": self.MAX_RADIUS_KM,
            "minmagnitude": 0.5,
            "maxmagnitude": 4.0,
            "eventtype": "quarry blast",   # critical filter
            "orderby": "time",
            "limit": 2000,
        }

        try:
            resp = self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise IngestorError(f"USGS FDSN blast query failed: {exc}") from exc

        points: list[TelemetryPoint] = []
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [None, None, None])
            try:
                # USGS uses milliseconds since epoch in properties.time
                ts = datetime.fromtimestamp(props["time"] / 1000.0, tz=__import__("datetime").timezone.utc)
                mag = float(props.get("mag", 0.0))
                title = props.get("title", "")
                points.append(
                    TelemetryPoint(
                        ts=ts,
                        signal_id=self.signal_id,
                        value=mag,
                        unit="magnitude",
                        source="real",
                        metadata={
                            "title": title,
                            "place": props.get("place"),
                            "lat": coords[1],
                            "lon": coords[0],
                            "depth_km": coords[2],
                            "url": props.get("url"),
                            "type": props.get("type"),
                        },
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue

        return points
