"""
Signal 01 — ADS-B High-Altitude over Prescott VOR (real OpenSky Network)
Free public endpoint. Returns current states in bbox.
For time-series we treat each collection as a point-in-time observation.
"""
from datetime import datetime, timezone

from .base import RealIngestor, IngestorError
from ..models import TelemetryPoint


class OpenSkyADSBIngestor(RealIngestor):
    signal_id = 1
    name = "ADS-B Traffic (OpenSky Network)"
    source_type = "real"

    # Prescott VOR (PRC) approx center
    # Slightly larger box to capture transit and training traffic
    LAMIN = 34.35
    LOMIN = -112.95
    LAMAX = 34.95
    LOMAX = -111.85

    def fetch(self, start: datetime, end: datetime) -> list[TelemetryPoint]:
        """
        OpenSky /states/all is a live snapshot (no time range on the free endpoint).
        We ignore the requested window for now and return the current observation
        as a single high-confidence real point + derived volume metric.
        """
        url = "https://opensky-network.org/api/states/all"
        params = {
            "lamin": self.LAMIN,
            "lomin": self.LOMIN,
            "lamax": self.LAMAX,
            "lomax": self.LOMAX,
        }

        try:
            resp = self.client.get(url, params=params)
            if resp.status_code == 429:
                raise IngestorError("OpenSky rate limited (try again in ~10s)")
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise IngestorError(f"OpenSky fetch failed: {exc}") from exc

        states = data.get("states") or []
        now = datetime.now(timezone.utc)
        count = len(states)

        # Simple altitude stats for high-alt transit flavor
        alts = []
        for s in states:
            if s[7] is not None:  # baro altitude
                alts.append(s[7])

        high_alt_count = sum(1 for a in alts if a and a > 8000)  # ft-ish
        avg_alt = sum(alts) / len(alts) if alts else 0

        point = TelemetryPoint(
            ts=now,
            signal_id=self.signal_id,
            value=float(count),
            unit="aircraft_in_bbox",
            source="real",
            metadata={
                "bbox": [self.LAMIN, self.LOMIN, self.LAMAX, self.LOMAX],
                "high_altitude_over_8000ft": high_alt_count,
                "avg_baro_alt_ft": round(avg_alt, 0) if avg_alt else None,
                "total_states": count,
                "note": "Live snapshot from OpenSky public API. Volume at collection time.",
            },
        )
        return [point]
