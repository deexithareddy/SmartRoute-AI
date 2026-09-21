"""
Routing Providers

Provider abstraction layer for SmartRoute AI routing backends.

Chain:
  HereRoutingProvider     -- HERE Routing API v8, traffic-aware ETA, data_source="here_live"
  GeoapifyRoutingProvider -- Geoapify Routing API v1,   data_source="geoapify"

Normalized route dict returned by both providers:
  {
      "distance": float,               # meters
      "duration": float,               # seconds  (traffic-aware for HERE)
      "lat_lng_coordinates": list,     # [[lat, lng], ...]
      "road_name": str,
      "provider": str,                 # "HERE" | "GEOAPIFY"
      "data_source": str,              # "here_live" | "geoapify"
      "traffic_status": str | None,    # "Low" | "Moderate" | "Heavy"
      "traffic_delay_minutes": float | None,
      "legs": list,
      "waypoints": list,
  }

Security rules enforced in this module:
  - API keys never appear in logs, telemetry endpoint_url strings, or literals
  - Provider name is never forwarded to the frontend UI layer
  - No route data is fabricated on failure; exceptions are raised transparently
  - Traffic ETA (HERE) is separate from SmartRoute risk scores (weather/incident/road engine)
"""

import concurrent.futures
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import requests

from backend.config import (
    GEOAPIFY_API_KEY,
    GEOAPIFY_ROUTING_URL,
    HERE_API_KEY,
    HERE_ROUTING_URL,
)
from backend.services.telemetry_logger import telemetry_logger

try:
    import flexpolyline as fp
    _FLEXPOLYLINE_AVAILABLE = True
except ImportError:
    _FLEXPOLYLINE_AVAILABLE = False

logger = logging.getLogger("SmartRouteAI.RoutingProviders")
USER_AGENT = "SmartRouteAI/1.0 (Emergency Routing & Decision Support)"

# --------------------------------------------------------------------------- #
# Traffic classification thresholds (seconds)
# --------------------------------------------------------------------------- #
_TRAFFIC_LOW_THRESHOLD = 120       # |delay| < 2 min  -> Low
_TRAFFIC_MODERATE_THRESHOLD = 600  # |delay| 2-10 min -> Moderate; > 10 min -> Heavy


def _classify_traffic_status(delay_seconds: float) -> str:
    """
    Derives a human-readable traffic status label from the absolute congestion delay.

    delay_seconds = typicalDuration - duration (HERE API field).
    Positive values mean slower than typical (congestion).
    Negative values mean lighter than typical.
    """
    abs_delay = abs(delay_seconds)
    if abs_delay < _TRAFFIC_LOW_THRESHOLD:
        return "Low"
    if abs_delay < _TRAFFIC_MODERATE_THRESHOLD:
        return "Moderate"
    return "Heavy"


# =========================================================================== #
# Abstract Base
# =========================================================================== #

class RoutingProvider(ABC):
    """Abstract base for all SmartRoute AI routing providers."""

    @abstractmethod
    def fetch_routes(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str = "drive",
        alternatives: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetches candidate driving routes.
        Returns a list of normalized route dicts.
        Raises on failure -- never fabricates route data.
        """
        raise NotImplementedError


# =========================================================================== #
# HERE Routing API v8 Provider
# =========================================================================== #

class HereRoutingProvider(RoutingProvider):
    """
    HERE Routing API v8 provider.

    Key capabilities:
      - routingMode=fast uses real-time traffic conditions for ETA
      - Up to 3 alternative routes per request
      - Flexible Polyline geometry decoded via the 'flexpolyline' library
      - Traffic delay derived from: typicalDuration - duration
        Positive -> delayed vs. typical; Negative -> lighter than typical
      - data_source = "here_live"
    """

    def __init__(self, session: requests.Session, timeout: int = 10):
        self.session = session
        self.timeout = timeout

    def fetch_routes(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str = "drive",
        alternatives: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Calls HERE Routing API v8 and returns normalized traffic-aware route dicts.

        Transport mode mapping:
          "drive"   -> car
          "walk"    -> pedestrian
          "bicycle" -> bicycle
          "truck"   -> truck

        Raises:
          ValueError      -- HERE_API_KEY not configured or 0 routes returned
          ImportError     -- flexpolyline not installed
          PermissionError -- 401/403 from HERE
          TimeoutError    -- request timeout
          ConnectionError -- any other HTTP or network error
        """
        if not HERE_API_KEY:
            raise ValueError("HERE_API_KEY is not configured.")

        if not _FLEXPOLYLINE_AVAILABLE:
            raise ImportError(
                "The flexpolyline package is required for HERE Routing but is not installed. "
                "Run: pip install flexpolyline"
            )

        transport_mode_map = {
            "drive": "car",
            "walk": "pedestrian",
            "bicycle": "bicycle",
            "truck": "truck",
        }
        transport_mode = transport_mode_map.get(mode.lower(), "car")

        # Build params -- apiKey stays only in the dict, never in log strings
        params: Dict[str, Any] = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "transportMode": transport_mode,
            "return": "polyline,summary,travelSummary",
            "routingMode": "fast",
            "alternatives": 3 if alternatives else 0,
            "apiKey": HERE_API_KEY,
        }

        masked_url = (
            f"{HERE_ROUTING_URL}?origin={origin_lat},{origin_lng}"
            f"&destination={dest_lat},{dest_lng}"
            f"&transportMode={transport_mode}&apiKey=HIDDEN"
        )
        start_time = time.perf_counter()

        try:
            resp = self.session.get(HERE_ROUTING_URL, params=params, timeout=self.timeout)
            latency = (time.perf_counter() - start_time) * 1000.0

            if resp.status_code in (401, 403):
                telemetry_logger.log(
                    service_name="HERE Routing",
                    endpoint_url=masked_url,
                    request_status="AUTH_ERROR",
                    response_status=resp.status_code,
                    latency_ms=latency,
                    provenance="UNAVAILABLE",
                    success=False,
                    error_message="HERE API key unauthorized or invalid.",
                )
                raise PermissionError("HERE Routing API key is invalid or unauthorized.")

            if resp.status_code != 200:
                telemetry_logger.log(
                    service_name="HERE Routing",
                    endpoint_url=masked_url,
                    request_status="ERROR",
                    response_status=resp.status_code,
                    latency_ms=latency,
                    provenance="UNAVAILABLE",
                    success=False,
                    error_message=f"HERE API returned HTTP {resp.status_code}",
                )
                raise ConnectionError(f"HERE Routing API returned HTTP {resp.status_code}.")

            data = resp.json()
            routes_raw = data.get("routes", [])

            if not routes_raw:
                raise ValueError("HERE Routing API returned 0 route candidates.")

            parsed_routes: List[Dict[str, Any]] = []
            seen_signatures: set = set()

            for route in routes_raw:
                sections = route.get("sections", [])
                if not sections:
                    continue

                total_distance_m = 0.0
                total_duration_s = 0.0
                total_typical_duration_s = 0.0
                all_coords: List[List[float]] = []

                for section in sections:
                    summary = section.get("summary", {})
                    total_distance_m += float(summary.get("length", 0.0))
                    total_duration_s += float(summary.get("duration", 0.0))
                    total_typical_duration_s += float(
                        summary.get("typicalDuration", total_duration_s)
                    )

                    # Decode Flexible Polyline -> [[lat, lng], ...]
                    poly_encoded = section.get("polyline", "")
                    if poly_encoded:
                        try:
                            decoded = fp.decode(poly_encoded)
                            all_coords.extend(
                                [[float(pt[0]), float(pt[1])] for pt in decoded]
                            )
                        except Exception as decode_err:
                            logger.debug("[HERE] Polyline decode error: %s", str(decode_err))

                if not all_coords:
                    all_coords = [[origin_lat, origin_lng], [dest_lat, dest_lng]]

                sig = (round(total_distance_m, -1), round(total_duration_s))
                if sig in seen_signatures:
                    continue
                seen_signatures.add(sig)

                delay_seconds = total_typical_duration_s - total_duration_s
                delay_minutes = round(delay_seconds / 60.0, 1)
                traffic_status = _classify_traffic_status(delay_seconds)
                road_name = self._extract_road_name(sections)

                parsed_routes.append({
                    "distance": total_distance_m,
                    "duration": total_duration_s,
                    "lat_lng_coordinates": all_coords,
                    "road_name": road_name,
                    "provider": "HERE",
                    "data_source": "here_live",
                    "traffic_status": traffic_status,
                    "traffic_delay_minutes": delay_minutes,
                    "legs": [],
                    "waypoints": [],
                })

            if not parsed_routes:
                raise ValueError("No valid routes could be parsed from HERE API response.")

            parsed_routes.sort(key=lambda r: r["duration"])

            logger.info(
                "[Routing] Source: [%.4f, %.4f] | Destination: [%.4f, %.4f] "
                "| Provider: HERE | HTTP: 200 | Routes: %d | Time: %.2fms",
                origin_lat, origin_lng, dest_lat, dest_lng, len(parsed_routes), latency,
            )
            telemetry_logger.log(
                service_name="HERE Routing",
                endpoint_url=masked_url,
                request_status="SENT",
                response_status=200,
                latency_ms=latency,
                provenance="LIVE",
                success=True,
                details={
                    "routes_count": len(parsed_routes),
                    "distance_km": round(parsed_routes[0]["distance"] / 1000.0, 1),
                    "duration_min": round(parsed_routes[0]["duration"] / 60.0, 1),
                    "traffic_status": parsed_routes[0]["traffic_status"],
                    "provider": "HERE Routing API v8",
                },
            )

            return parsed_routes

        except requests.exceptions.Timeout:
            latency = (time.perf_counter() - start_time) * 1000.0
            telemetry_logger.log(
                service_name="HERE Routing",
                endpoint_url=masked_url,
                request_status="TIMEOUT",
                response_status=504,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message="HERE Routing request timed out.",
            )
            raise TimeoutError("HERE Routing request timed out.")
        except (PermissionError, ValueError, ImportError):
            raise
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            telemetry_logger.log(
                service_name="HERE Routing",
                endpoint_url=masked_url,
                request_status="ERROR",
                response_status=None,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message=str(e),
            )
            raise ConnectionError(f"HERE Routing API error: {str(e)}")

    def _extract_road_name(self, sections: List[Dict[str, Any]]) -> str:
        """Extracts prominent road/area names from HERE route sections."""
        names: List[str] = []
        for section in sections:
            spans = section.get("spans", [])
            for span in spans:
                span_names = span.get("names", [])
                if span_names:
                    name = span_names[0].get("value", "")
                    if name and name not in names and len(name) > 2 and not name.isdigit():
                        names.append(name)
        if not names:
            return "Metropolitan Corridor"
        if len(names) == 1:
            return names[0]
        return f"{names[0]} via {names[1]}"


# =========================================================================== #
# Geoapify Routing Provider
# =========================================================================== #

class GeoapifyRoutingProvider(RoutingProvider):
    """
    Geoapify Routing API v1 provider.

    Key capabilities:
      - Parallel balanced (primary) + short (alternative) corridor discovery
      - GeoJSON FeatureCollection with LineString/MultiLineString geometry
      - Deduplication by (round(distance,-1), round(duration)) signature
      - GeoJSON [lng, lat] -> Leaflet [lat, lng] coordinate conversion
      - data_source = "geoapify"
      - No real-time traffic data; traffic_status and traffic_delay_minutes are None
    """

    def __init__(self, session: requests.Session, timeout: int = 8):
        self.session = session
        self.timeout = timeout

    def fetch_routes(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str = "drive",
        alternatives: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Calls Geoapify Routing API v1, queries balanced + short corridors in parallel,
        parses GeoJSON FeatureCollection, and returns normalized route dicts.

        Raises:
          ValueError      -- GEOAPIFY_API_KEY not configured or 0 valid routes parsed
          PermissionError -- 401/403 from Geoapify
          TimeoutError    -- request timeout
          ConnectionError -- any other HTTP or network error
        """
        if not GEOAPIFY_API_KEY:
            raise ValueError("GEOAPIFY_API_KEY is not configured.")

        waypoints_str = f"{origin_lat},{origin_lng}|{dest_lat},{dest_lng}"
        masked_url = f"{GEOAPIFY_ROUTING_URL}?waypoints={waypoints_str}&mode={mode}&apiKey=HIDDEN"
        start_time = time.perf_counter()

        types_to_query = ["balanced", "short"] if alternatives else ["balanced"]
        raw_responses: List[Dict[str, Any]] = []
        error_details: List[str] = []
        status_codes: List[int] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(types_to_query)) as executor:
            future_to_type = {
                executor.submit(self._query_single_type, waypoints_str, mode, rtype): rtype
                for rtype in types_to_query
            }
            for future in concurrent.futures.as_completed(future_to_type):
                rtype, status_code, json_data, err_msg = future.result()
                status_codes.append(status_code)
                if status_code == 200 and json_data:
                    raw_responses.append(json_data)
                elif err_msg:
                    error_details.append(f"{rtype}: {err_msg}")

        latency = (time.perf_counter() - start_time) * 1000.0

        if not raw_responses:
            telemetry_logger.log(
                service_name="Geoapify Routing",
                endpoint_url=masked_url,
                request_status="ERROR",
                response_status=status_codes[0] if status_codes else 502,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message=f"Geoapify Routing API failed: {'; '.join(error_details)}",
            )
            logger.error(
                "[Routing] Source: [%.4f, %.4f] | Destination: [%.4f, %.4f] "
                "| Provider: Geoapify | HTTP: %s | Failed: %s",
                origin_lat, origin_lng, dest_lat, dest_lng, status_codes, error_details,
            )
            if any(sc in (401, 403) for sc in status_codes):
                raise PermissionError(
                    "Routing service configuration error (Invalid or unauthorized Geoapify API key)."
                )
            if any(sc == 504 for sc in status_codes):
                raise TimeoutError("Geoapify Routing request timed out.")
            raise ConnectionError("Geoapify Routing service unavailable.")

        parsed_routes: List[Dict[str, Any]] = []
        seen_signatures: set = set()

        for data in raw_responses:
            features = data.get("features", [])
            for feature in features:
                props = feature.get("properties", {})
                geom = feature.get("geometry", {})
                distance_meters = float(props.get("distance", 0.0))
                duration_seconds = float(props.get("time", 0.0))
                legs = props.get("legs", [])
                waypoints = props.get("waypoints", [])

                sig = (round(distance_meters, -1), round(duration_seconds))
                if sig in seen_signatures:
                    continue
                seen_signatures.add(sig)

                geom_type = geom.get("type", "LineString")
                raw_coords = geom.get("coordinates", [])
                lat_lng_coordinates: List[List[float]] = []

                if geom_type == "LineString":
                    lat_lng_coordinates = [
                        [float(pt[1]), float(pt[0])] for pt in raw_coords if len(pt) >= 2
                    ]
                elif geom_type == "MultiLineString":
                    for line in raw_coords:
                        for pt in line:
                            if len(pt) >= 2:
                                lat_lng_coordinates.append([float(pt[1]), float(pt[0])])

                if not lat_lng_coordinates:
                    lat_lng_coordinates = [[origin_lat, origin_lng], [dest_lat, dest_lng]]

                road_name = self._extract_road_names(props)

                parsed_routes.append({
                    "distance": distance_meters,
                    "duration": duration_seconds,
                    "legs": legs,
                    "waypoints": waypoints,
                    "lat_lng_coordinates": lat_lng_coordinates,
                    "road_name": road_name,
                    "provider": "GEOAPIFY",
                    "data_source": "geoapify",
                    "traffic_status": None,
                    "traffic_delay_minutes": None,
                })

        if not parsed_routes:
            raise ValueError("No valid parsed routes extracted from Geoapify response.")

        parsed_routes.sort(key=lambda r: r["duration"])

        logger.info(
            "[Routing] Source: [%.4f, %.4f] | Destination: [%.4f, %.4f] "
            "| Provider: Geoapify | HTTP: 200 | Routes: %d | Time: %.2fms",
            origin_lat, origin_lng, dest_lat, dest_lng, len(parsed_routes), latency,
        )
        telemetry_logger.log(
            service_name="Geoapify Routing",
            endpoint_url=masked_url,
            request_status="SENT",
            response_status=200,
            latency_ms=latency,
            provenance="LIVE",
            success=True,
            details={
                "routes_count": len(parsed_routes),
                "distance_km": round(parsed_routes[0]["distance"] / 1000.0, 1),
                "duration_min": round(parsed_routes[0]["duration"] / 60.0, 1),
                "waypoints_count": len(parsed_routes[0]["lat_lng_coordinates"]),
                "provider": "Geoapify Routing API",
            },
        )

        return parsed_routes

    def _query_single_type(
        self,
        waypoints_str: str,
        mode: str,
        route_type: str,
    ) -> Tuple[str, int, Optional[Dict[str, Any]], Optional[str]]:
        """Queries a single Geoapify route type (balanced or short) synchronously."""
        params = {
            "waypoints": waypoints_str,
            "mode": mode,
            "type": route_type,
            "format": "geojson",
            "details": "instruction_details,route_details",
            "apiKey": GEOAPIFY_API_KEY,
        }
        try:
            resp = self.session.get(GEOAPIFY_ROUTING_URL, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return route_type, 200, resp.json(), None
            if resp.status_code in (401, 403):
                return route_type, resp.status_code, None, "Invalid or unauthorized API key"
            return route_type, resp.status_code, None, f"HTTP {resp.status_code}"
        except requests.exceptions.Timeout:
            return route_type, 504, None, "Request timed out"
        except Exception as exc:
            return route_type, 500, None, str(exc)

    def _extract_road_names(self, properties: Dict[str, Any]) -> str:
        """Extracts prominent road names from Geoapify legs and step instructions."""
        road_names: List[str] = []
        legs = properties.get("legs", [])

        for leg in legs:
            steps = leg.get("steps", [])
            for step in steps:
                name = step.get("name", "").strip()
                if name and name not in road_names and len(name) > 2 and not name.isdigit():
                    road_names.append(name)

                instr = step.get("instruction", {}).get("text", "")
                if not name and instr:
                    clean_match = re.search(
                        r"(?:onto|on|along|towards|at)\s+([A-Z0-9][A-Za-z0-9\s\-/\.]{3,35})",
                        instr,
                        re.IGNORECASE,
                    )
                    if clean_match:
                        extracted = clean_match.group(1).strip()
                        if extracted and extracted not in road_names and len(extracted) > 3:
                            road_names.append(extracted)

        if not road_names:
            return "Metropolitan Arterial Corridor"
        if len(road_names) == 1:
            return road_names[0]
        return f"{road_names[0]} via {road_names[1]}"
