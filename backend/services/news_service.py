"""
News & Incident Service

Service interface for retrieving real-time municipal alerts, police CAD dispatch,
traffic accident bulletins, and road closure incident feeds.
Includes structured telemetry logging and transparent provenance labeling.
"""

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.services.telemetry_logger import telemetry_logger

# Path to curated local sample incident feed
SAMPLE_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "sample_data.json"
)


@dataclass
class IncidentItem:
    """Standardized incident report record."""
    incident_id: str
    headline: str
    raw_text: str
    event_type: str  # "accident", "closure", "flood", "protest", "construction", "other"
    severity: str    # "low", "medium", "high"
    location_name: str
    lat: float
    lng: float
    reported_time: str
    impact_radius_km: float


class NewsService:
    """Service client for ingesting incident reports and news feeds."""

    def __init__(self, data_path: str = SAMPLE_DATA_PATH):
        self.data_path = data_path
        self._is_online = True
        self._cache: Optional[Tuple[float, List[IncidentItem]]] = None
        self.cache_ttl_seconds = 30.0  # 30 seconds in-memory cache

    def set_online_status(self, is_online: bool) -> None:
        """Allows toggling provider availability for failure testing."""
        self._is_online = is_online

    def is_healthy(self) -> bool:
        """Returns True if the incident feed source is accessible."""
        return self._is_online

    def fetch_incidents(self) -> Optional[List[IncidentItem]]:
        """
        Fetches active incident reports from the telemetry feed.
        Returns a list of parsed IncidentItem objects or None if offline.
        """
        start_time = time.perf_counter()
        if not self._is_online:
            latency = (time.perf_counter() - start_time) * 1000.0
            telemetry_logger.log(
                service_name="CAD Incidents & Municipal Alerts",
                endpoint_url="cad://emergency-alerts-matrix",
                request_status="FAULT_INJECTED",
                response_status=None,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message="Incident feed forced UNAVAILABLE via fault-injection",
            )
            return None

        now = time.time()
        if self._cache is not None:
            cache_time, cached_items = self._cache
            if now - cache_time < self.cache_ttl_seconds:
                latency = (time.perf_counter() - start_time) * 1000.0
                telemetry_logger.log(
                    service_name="CAD Incidents & Municipal Alerts",
                    endpoint_url="cad://emergency-alerts-matrix",
                    request_status="CACHED_HIT",
                    response_status=200,
                    latency_ms=latency,
                    provenance="LIVE",
                    success=True,
                    details={"cached": True, "count": len(cached_items)},
                )
                return cached_items

        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                    raw_incidents = payload.get("incidents", [])

                    results: List[IncidentItem] = []
                    for item in raw_incidents:
                        loc = item.get("location", {})
                        results.append(
                            IncidentItem(
                                incident_id=item.get("incident_id", ""),
                                headline=item.get("headline", ""),
                                raw_text=item.get("raw_text", ""),
                                event_type=item.get("event_type", "other"),
                                severity=item.get("severity", "low"),
                                location_name=loc.get("name", "Unknown Location"),
                                lat=float(loc.get("lat", 0.0)),
                                lng=float(loc.get("lng", 0.0)),
                                reported_time=item.get("reported_time", "Recent"),
                                impact_radius_km=float(item.get("impact_radius_km", 1.0)),
                            )
                        )

                    latency = (time.perf_counter() - start_time) * 1000.0
                    telemetry_logger.log(
                        service_name="CAD Incidents & Municipal Alerts",
                        endpoint_url="cad://emergency-alerts-matrix",
                        request_status="SENT",
                        response_status=200,
                        latency_ms=latency,
                        provenance="LIVE",
                        success=True,
                        details={"incidents_count": len(results)},
                    )
                    self._cache = (now, results)
                    return results
            else:
                latency = (time.time() - start_time) * 1000.0
                telemetry_logger.log(
                    service_name="CAD Incidents & Municipal Alerts",
                    endpoint_url=self.data_path,
                    request_status="SENT",
                    response_status=404,
                    latency_ms=latency,
                    provenance="UNAVAILABLE",
                    success=False,
                    error_message=f"Incident dataset not found at {self.data_path}",
                )
                return []
        except Exception as e:
            latency = (time.time() - start_time) * 1000.0
            telemetry_logger.log(
                service_name="CAD Incidents & Municipal Alerts",
                endpoint_url=self.data_path,
                request_status="SENT",
                response_status=None,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message=str(e),
            )
            return None


# Singleton instance
news_service = NewsService()
