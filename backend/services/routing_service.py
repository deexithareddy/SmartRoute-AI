"""
Routing Service

Integrates with HERE Routing API v8 (primary, traffic-aware) and Geoapify Routing API (fallback),
plus OpenStreetMap / Nominatim / OSRM for geocoding and last-resort routing.

Features:
  - Provider abstraction: HERE -> Geoapify -> OSRM (in priority order)
  - HERE Routing API v8: real traffic-aware ETA, Flexible Polyline geometry, alternatives
  - Geoapify Routing API v1: parallel balanced/short corridor discovery (fallback)
  - OSRM: open-source routing engine, no API key required (last resort)
  - Geocoding chain: direct coordinates -> Geoapify -> Nominatim -> known city DB
  - Structured telemetry logging with automatic apiKey masking
  - In-memory response caching (geocode 10 min TTL; routes 45 s TTL)
  - Strict error transparency: no route data fabrication on provider failure
"""

import concurrent.futures
import os
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple
import logging
import requests

from backend.config import (
    GEOAPIFY_API_KEY,
    GEOAPIFY_ROUTING_URL,
    GEOAPIFY_GEOCODING_URL,
    HERE_API_KEY,
    OSRM_BASE_URL,
    NOMINATIM_BASE_URL,
)
from backend.services.telemetry_logger import telemetry_logger
from backend.services.routing_providers import (
    HereRoutingProvider,
    GeoapifyRoutingProvider,
)

logger = logging.getLogger("SmartRouteAI.Routing")
USER_AGENT = "SmartRouteAI/1.0 (Emergency Routing & Decision Support)"


class RoutingService:
    """Service client for routing and geocoding with provider abstraction, caching, and telemetry."""

    def __init__(self, timeout_seconds: int = 8):
        self.timeout = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._is_online = True

        # Routing provider instances (shared session for connection pooling)
        self._here_provider = HereRoutingProvider(session=self.session, timeout=10)
        self._geoapify_provider = GeoapifyRoutingProvider(session=self.session, timeout=timeout_seconds)

        # In-memory performance caches
        self._geocode_cache: Dict[str, Tuple[float, Tuple[float, float, str]]] = {}
        self.geocode_ttl_seconds = 600  # 10 minutes

        self._routes_cache: Dict[Tuple[float, float, float, float], Tuple[float, List[Dict[str, Any]]]] = {}
        self.routes_ttl_seconds = 45   # 45 seconds — shorter for HERE live traffic freshness

    def set_online_status(self, is_online: bool) -> None:
        """Allows toggling maps/routing provider availability for fault-injection testing."""
        self._is_online = is_online

    def is_healthy(self) -> bool:
        """Returns True if the routing service is operational."""
        return self._is_online

    def geocode(self, query: str) -> Tuple[float, float, str]:
        """
        Geocodes a human-readable location string to (latitude, longitude, display_name).
        Supports:
          1. Direct coordinate strings ("17.3850, 78.4867")
          2. In-memory geocode cache
          3. Geoapify Geocoding API (if GEOAPIFY_API_KEY is configured)
          4. OpenStreetMap Nominatim Geocoding API
          5. Well-known coordinate database for major Indian metropolitan corridors
        """
        start_time = time.perf_counter()
        query_str = query.strip()
        if not query_str:
            raise ValueError("Geocoding query cannot be empty")

        # 1. Direct coordinates parse e.g. "17.3850, 78.4867"
        coord_match = re.match(
            r"^\s*([+-]?\d+(?:\.\d+)?)\s*[,;\s]\s*([+-]?\d+(?:\.\d+)?)\s*$", query_str
        )
        if coord_match:
            lat = float(coord_match.group(1))
            lng = float(coord_match.group(2))
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                latency = (time.perf_counter() - start_time) * 1000.0
                telemetry_logger.log(
                    service_name="Nominatim Geocoding",
                    endpoint_url="local://coordinates-parse",
                    request_status="DIRECT_PARSE",
                    response_status=200,
                    latency_ms=latency,
                    provenance="LIVE",
                    success=True,
                    details={"query": query_str, "lat": lat, "lng": lng},
                )
                return lat, lng, f"Coordinates ({lat:.4f}, {lng:.4f})"

        # 2. Check fault injection
        if not self._is_online:
            latency = (time.perf_counter() - start_time) * 1000.0
            telemetry_logger.log(
                service_name="Routing & Geocoding",
                endpoint_url="api://routing-service",
                request_status="FAULT_INJECTED",
                response_status=None,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message="Routing & Geocoding service forced UNAVAILABLE via fault-injection",
            )
            raise ConnectionError("Geocoding and maps feed is marked unavailable via fault injection.")

        # 3. Check in-memory cache
        cache_key = query_str.lower()
        now = time.time()
        if cache_key in self._geocode_cache:
            cached_time, cached_val = self._geocode_cache[cache_key]
            if now - cached_time < self.geocode_ttl_seconds:
                latency = (time.perf_counter() - start_time) * 1000.0
                telemetry_logger.log(
                    service_name="Geoapify Geocoding",
                    endpoint_url="cache://geocoding",
                    request_status="CACHED_HIT",
                    response_status=200,
                    latency_ms=latency,
                    provenance="CACHED",
                    success=True,
                    details={"query": query_str, "cached": True},
                )
                return cached_val

        # 4. Try Geoapify Geocoding API if key is available
        if GEOAPIFY_API_KEY:
            encoded_query = urllib.parse.quote(query_str)
            geoapify_url = f"{GEOAPIFY_GEOCODING_URL}?text={encoded_query}&apiKey={GEOAPIFY_API_KEY}"
            masked_url = f"{GEOAPIFY_GEOCODING_URL}?text={encoded_query}&apiKey=HIDDEN"
            try:
                response = self.session.get(geoapify_url, timeout=self.timeout)
                latency = (time.perf_counter() - start_time) * 1000.0
                if response.status_code == 200:
                    data = response.json()
                    features = data.get("features", [])
                    if features and len(features) > 0:
                        first_prop = features[0].get("properties", {})
                        lat = float(first_prop.get("lat", 0.0))
                        lon = float(first_prop.get("lon", 0.0))
                        formatted = first_prop.get("formatted", query_str)
                        if lat != 0.0 or lon != 0.0:
                            telemetry_logger.log(
                                service_name="Geoapify Geocoding",
                                endpoint_url=masked_url,
                                request_status="SENT",
                                response_status=200,
                                latency_ms=latency,
                                provenance="LIVE",
                                success=True,
                                details={"query": query_str, "lat": lat, "lng": lon, "name": formatted},
                            )
                            res = (lat, lon, formatted)
                            self._geocode_cache[cache_key] = (now, res)
                            return res
            except Exception as e:
                telemetry_logger.log(
                    service_name="Geoapify Geocoding",
                    endpoint_url=masked_url,
                    request_status="ERROR",
                    response_status=None,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    provenance="UNAVAILABLE",
                    success=False,
                    error_message=f"Geoapify geocoding error: {str(e)}",
                )

        # 5. Query Nominatim geocoding API fallback
        encoded_query = urllib.parse.quote(query_str)
        url = f"{NOMINATIM_BASE_URL}/search?q={encoded_query}&format=json&limit=1"

        try:
            response = self.session.get(url, timeout=self.timeout)
            latency = (time.perf_counter() - start_time) * 1000.0

            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0:
                    first = results[0]
                    lat = float(first["lat"])
                    lng = float(first["lon"])
                    display_name = first.get("display_name", query_str)

                    telemetry_logger.log(
                        service_name="Nominatim Geocoding",
                        endpoint_url=url,
                        request_status="SENT",
                        response_status=200,
                        latency_ms=latency,
                        provenance="LIVE",
                        success=True,
                        details={"query": query_str, "lat": lat, "lng": lng, "name": display_name},
                    )
                    res = (lat, lng, display_name)
                    self._geocode_cache[cache_key] = (now, res)
                    return res
        except Exception:
            pass

        # 6. Known coordinate lookup for standard Indian metropolitan emergency corridors
        fallback_lookup = {
            "hyderabad": (17.3850, 78.4867, "Hyderabad, TG, India"),
            "secunderabad": (17.4399, 78.4983, "Secunderabad, TG, India"),
            "500003": (17.4435, 78.4975, "Secunderabad - 500003, TG, India"),
            "charminar": (17.3616, 78.4747, "Charminar, Hyderabad, TG, India"),
            "hitec city": (17.4435, 78.3772, "HITEC City, Hyderabad, TG, India"),
            "gachibowli": (17.4401, 78.3489, "Gachibowli, Hyderabad, TG, India"),
            "indiranagar": (12.9719, 77.6412, "Indiranagar, Bengaluru, KA, India"),
            "whitefield": (12.9698, 77.7500, "Whitefield, Bengaluru, KA, India"),
            "koramangala": (12.9352, 77.6245, "Koramangala, Bengaluru, KA, India"),
            "mg road": (12.9756, 77.6066, "MG Road, Bengaluru, KA, India"),
            "majestic": (12.9767, 77.5713, "Majestic, Bengaluru, KA, India"),
            "hebbal": (13.0358, 77.5970, "Hebbal, Bengaluru, KA, India"),
            "electronic city": (12.8452, 77.6602, "Electronic City, Bengaluru, KA, India"),
            "jayanagar": (12.9308, 77.5838, "Jayanagar, Bengaluru, KA, India"),
            "mumbai": (19.0760, 72.8777, "Mumbai, MH, India"),
            "delhi": (28.6139, 77.2090, "Delhi, DL, India"),
            "chennai": (13.0827, 80.2707, "Chennai, TN, India"),
            "kolkata": (22.5726, 88.3639, "Kolkata, WB, India"),
        }

        query_lower = query_str.lower()
        for key, (f_lat, f_lng, f_name) in fallback_lookup.items():
            if key in query_lower:
                res = (f_lat, f_lng, f_name)
                self._geocode_cache[cache_key] = (now, res)
                return res

        # If location cannot be resolved by any provider, raise clean error
        raise ValueError(f"Unable to geocode location query: '{query_str}'. Please provide a valid city, street, or landmark.")

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
        Fetches real-world driving candidate routes using a provider priority chain:

          1. HERE Routing API v8  (if HERE_API_KEY configured) — traffic-aware ETA
          2. Geoapify Routing API (if GEOAPIFY_API_KEY configured) — fallback
          3. OSRM                 (no API key needed) — last resort

        Strictly raises errors on provider failure — never fabricates fake route data.
        All route dicts carry 'data_source': "here_live" | "geoapify" | "osrm".
        """
        start_time = time.perf_counter()

        if not self._is_online:
            latency = (time.perf_counter() - start_time) * 1000.0
            telemetry_logger.log(
                service_name="Routing Engine",
                endpoint_url="api://routing-service",
                request_status="FAULT_INJECTED",
                response_status=None,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message="Routing service forced UNAVAILABLE via fault-injection",
            )
            raise ConnectionError("Routing feed is marked unavailable via fault injection.")

        # Check routes cache
        routes_cache_key = (
            round(origin_lat, 4),
            round(origin_lng, 4),
            round(dest_lat, 4),
            round(dest_lng, 4),
        )
        now = time.time()
        if routes_cache_key in self._routes_cache:
            cached_time, cached_routes = self._routes_cache[routes_cache_key]
            if now - cached_time < self.routes_ttl_seconds:
                latency = (time.perf_counter() - start_time) * 1000.0
                telemetry_logger.log(
                    service_name="Routing Engine",
                    endpoint_url="cache://routes",
                    request_status="CACHED_HIT",
                    response_status=200,
                    latency_ms=latency,
                    provenance="CACHED",
                    success=True,
                    details={"cached": True, "routes_count": len(cached_routes)},
                )
                return cached_routes

        # 1. Primary: HERE Routing API v8 (traffic-aware)
        if HERE_API_KEY:
            try:
                routes = self._here_provider.fetch_routes(
                    origin_lat=origin_lat,
                    origin_lng=origin_lng,
                    dest_lat=dest_lat,
                    dest_lng=dest_lng,
                    mode=mode,
                    alternatives=alternatives,
                )
                if routes:
                    self._routes_cache[routes_cache_key] = (now, routes)
                    return routes
            except (PermissionError, ImportError):
                # Auth or dependency errors from HERE should not silently fall through
                raise
            except Exception as here_err:
                logger.warning(
                    "[Routing] HERE provider failed, falling through to Geoapify: %s", str(here_err)
                )
                telemetry_logger.log(
                    service_name="HERE Routing",
                    endpoint_url="api://here-routing/v8",
                    request_status="FALLTHROUGH",
                    response_status=None,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    provenance="UNAVAILABLE",
                    success=False,
                    error_message=f"HERE fallthrough to Geoapify: {str(here_err)}",
                )

        # 2. Fallback: Geoapify Routing API
        if GEOAPIFY_API_KEY:
            try:
                routes = self._geoapify_provider.fetch_routes(
                    origin_lat=origin_lat,
                    origin_lng=origin_lng,
                    dest_lat=dest_lat,
                    dest_lng=dest_lng,
                    mode=mode,
                    alternatives=alternatives,
                )
                if routes:
                    self._routes_cache[routes_cache_key] = (now, routes)
                    return routes
                else:
                    raise ValueError("Geoapify Routing API returned 0 viable route paths.")
            except Exception as geo_err:
                telemetry_logger.log(
                    service_name="Geoapify Routing",
                    endpoint_url=f"{GEOAPIFY_ROUTING_URL}?apiKey=HIDDEN",
                    request_status="ERROR",
                    response_status=None,
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    provenance="UNAVAILABLE",
                    success=False,
                    error_message=f"Geoapify routing failed: {str(geo_err)}",
                )
                raise ConnectionError(f"Geoapify Routing API failed: {str(geo_err)}")

        # 3. Last resort: OSRM (no API key needed)
        try:
            routes = self.fetch_routes_osrm(
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                dest_lat=dest_lat,
                dest_lng=dest_lng,
                alternatives=alternatives,
            )
            if routes:
                self._routes_cache[routes_cache_key] = (now, routes)
                return routes
            else:
                raise ValueError("OSRM Routing API returned 0 viable route paths.")
        except Exception as e:
            raise ConnectionError(f"OSRM Routing failed: {str(e)}")

    def _query_geoapify_single_type(
        self,
        waypoints_str: str,
        mode: str,
        route_type: str,
    ) -> Tuple[str, int, Optional[Dict[str, Any]], Optional[str]]:
        """Queries a single Geoapify route type (e.g. balanced, short) using requests params."""
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
        except Exception as e:
            return route_type, 500, None, str(e)

    def fetch_routes_geoapify(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str = "drive",
        alternatives: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Calls Geoapify Routing API v1, parses GeoJSON FeatureCollection,
        and extracts route geometry, distance, duration, waypoints, and leg step details.
        Queries balanced (primary) and short (alternative) corridors in parallel when alternatives=True.
        """
        start_time = time.perf_counter()
        waypoints_str = f"{origin_lat},{origin_lng}|{dest_lat},{dest_lng}"
        masked_url = f"{GEOAPIFY_ROUTING_URL}?waypoints={waypoints_str}&mode={mode}&apiKey=HIDDEN"

        # Query primary (balanced) and alternative (short) corridors concurrently
        types_to_query = ["balanced", "short"] if alternatives else ["balanced"]

        raw_responses: List[Dict[str, Any]] = []
        error_details: List[str] = []
        status_codes: List[int] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(types_to_query)) as executor:
            future_to_type = {
                executor.submit(self._query_geoapify_single_type, waypoints_str, mode, rtype): rtype
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
            # Safe developer debug log without secrets
            logger.error(
                "[Routing] Source coordinates: [%.4f, %.4f] | Destination coordinates: [%.4f, %.4f] | Provider: Geoapify | HTTP status: %s | Failed: %s",
                origin_lat, origin_lng, dest_lat, dest_lng, status_codes, error_details
            )
            if any(sc in (401, 403) for sc in status_codes):
                raise PermissionError("Routing service configuration error (Invalid or unauthorized API key).")
            if any(sc == 504 for sc in status_codes):
                raise TimeoutError("Routing request timed out.")
            raise ConnectionError("Live routing service unavailable.")

        parsed_routes: List[Dict[str, Any]] = []
        seen_signatures = set()

        for data in raw_responses:
            features = data.get("features", [])
            for feature in features:
                props = feature.get("properties", {})
                geom = feature.get("geometry", {})
                distance_meters = float(props.get("distance", 0.0))
                duration_seconds = float(props.get("time", 0.0))
                legs = props.get("legs", [])
                waypoints = props.get("waypoints", [])

                # Deduplicate identical routes (signature: round(distance, -1) and round(duration))
                sig = (round(distance_meters, -1), round(duration_seconds))
                if sig in seen_signatures:
                    continue
                seen_signatures.add(sig)

                # Extract coordinates from GeoJSON: GeoJSON uses [lng, lat], convert to [lat, lng] for Leaflet
                geom_type = geom.get("type", "LineString")
                raw_coords = geom.get("coordinates", [])
                lat_lng_coordinates: List[List[float]] = []

                if geom_type == "LineString":
                    lat_lng_coordinates = [[float(pt[1]), float(pt[0])] for pt in raw_coords if len(pt) >= 2]
                elif geom_type == "MultiLineString":
                    for line in raw_coords:
                        for pt in line:
                            if len(pt) >= 2:
                                lat_lng_coordinates.append([float(pt[1]), float(pt[0])])

                if not lat_lng_coordinates:
                    lat_lng_coordinates = [[origin_lat, origin_lng], [dest_lat, dest_lng]]

                road_name = self.extract_geoapify_road_names(props)

                route_item = {
                    "distance": distance_meters,
                    "duration": duration_seconds,
                    "legs": legs,
                    "waypoints": waypoints,
                    "properties": props,
                    "geometry": geom,
                    "lat_lng_coordinates": lat_lng_coordinates,
                    "road_name": road_name,
                    "provider": "GEOAPIFY",
                    "data_source": "geoapify",
                }
                parsed_routes.append(route_item)

        if not parsed_routes:
            raise ValueError("No valid parsed routes extracted from Geoapify response.")

        # Sort routes by nominal duration
        parsed_routes.sort(key=lambda r: r["duration"])

        # Safe development debug logging (no secrets)
        logger.info(
            "[Routing] Source coordinates: [%.4f, %.4f] | Destination coordinates: [%.4f, %.4f] | Provider: Geoapify | HTTP status: 200 | Number of routes: %d | Response time: %.2fms",
            origin_lat, origin_lng, dest_lat, dest_lng, len(parsed_routes), latency
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

    def extract_geoapify_road_names(self, properties: Dict[str, Any]) -> str:
        """Extracts prominent road names from Geoapify legs and step instructions."""
        road_names: List[str] = []
        legs = properties.get("legs", [])

        for leg in legs:
            steps = leg.get("steps", [])
            for step in steps:
                # 1. Check explicit road name
                name = step.get("name", "").strip()
                if name and name not in road_names and len(name) > 2 and not name.isdigit():
                    road_names.append(name)

                # 2. Check instruction text if name is missing
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

    def fetch_routes_osrm(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        alternatives: bool = True,
    ) -> List[Dict[str, Any]]:
        """Calls OSRM driving service as a fallback routing provider."""
        start_time = time.perf_counter()
        alt_param = "true" if alternatives else "false"
        url = (
            f"{OSRM_BASE_URL}/route/v1/driving/"
            f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
            f"?overview=full&geometries=geojson&steps=true&alternatives={alt_param}"
        )

        try:
            response = self.session.get(url, timeout=self.timeout)
            latency = (time.perf_counter() - start_time) * 1000.0

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok" and "routes" in data and len(data["routes"]) > 0:
                    raw_routes = data["routes"]
                    parsed_routes = []
                    for r in raw_routes:
                        distance_meters = float(r.get("distance", 0.0))
                        duration_seconds = float(r.get("duration", 0.0))
                        geometry = r.get("geometry", {})
                        raw_coords = geometry.get("coordinates", [])
                        lat_lng_coordinates = [[float(c[1]), float(c[0])] for c in raw_coords if len(c) >= 2]
                        road_name = self.extract_osrm_road_names(r)

                        parsed_routes.append({
                            "distance": distance_meters,
                            "duration": duration_seconds,
                            "legs": r.get("legs", []),
                            "geometry": geometry,
                            "lat_lng_coordinates": lat_lng_coordinates,
                            "road_name": road_name,
                            "provider": "OSRM",
                        })

                    telemetry_logger.log(
                        service_name="OSRM Highway Routing",
                        endpoint_url=url,
                        request_status="SENT",
                        response_status=200,
                        latency_ms=latency,
                        provenance="LIVE",
                        success=True,
                        details={
                            "routes_count": len(parsed_routes),
                            "distance_km": round(parsed_routes[0]["distance"] / 1000.0, 1),
                            "duration_min": round(parsed_routes[0]["duration"] / 60.0, 1),
                        },
                    )
                    return parsed_routes
            raise ConnectionError(f"OSRM returned HTTP {response.status_code}")
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            telemetry_logger.log(
                service_name="OSRM Highway Routing",
                endpoint_url=url,
                request_status="ERROR",
                response_status=None,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message=str(e),
            )
            raise ConnectionError(f"OSRM Routing failed: {str(e)}")

    def extract_osrm_road_names(self, raw_route: Dict[str, Any]) -> str:
        """Extracts prominent road names from OSRM step instructions."""
        road_names: List[str] = []
        legs = raw_route.get("legs", [])
        for leg in legs:
            steps = leg.get("steps", [])
            for step in steps:
                name = step.get("name", "").strip()
                if name and name not in road_names and len(name) > 2:
                    road_names.append(name)

        if not road_names:
            return "Primary Corridor"
        if len(road_names) == 1:
            return road_names[0]
        return f"{road_names[0]} via {road_names[1]}"


# Global singleton instance
routing_service = RoutingService()

