"""
Route Agent

Generates candidate routes between source and destination via routing provider
(Geoapify Routing API with OSRM fallback), strictly answering "what routes exist"
without evaluating multi-criteria risk or picking winners.
"""

import concurrent.futures
from typing import Dict, List, Tuple
from backend.services.routing_service import routing_service
from backend.models.schemas import RouteResult, RiskFactors

ROUTE_COLOR_PALETTE = [
    "#ef4444",  # Route A - Red/Coral
    "#10b981",  # Route B - Emerald Green
    "#f59e0b",  # Route C - Amber/Gold
    "#38bdf8",  # Route D - Cyan
    "#a855f7",  # Route E - Purple
]

ROUTE_LETTERS = ["A", "B", "C", "D", "E"]

# Hyderabad Metropolitan Area Operational Bounds
HYDERABAD_MIN_LAT = 16.80
HYDERABAD_MAX_LAT = 17.90
HYDERABAD_MIN_LNG = 78.00
HYDERABAD_MAX_LNG = 79.00


def is_within_hyderabad_metro(lat: float, lng: float) -> bool:
    """Validates if coordinates reside within the Hyderabad metropolitan operational region."""
    return (HYDERABAD_MIN_LAT <= lat <= HYDERABAD_MAX_LAT) and (HYDERABAD_MIN_LNG <= lng <= HYDERABAD_MAX_LNG)


class RouteAgent:
    """
    Route Agent responsible for candidate route generation.
    Strictly answers 'what routes exist' within Hyderabad without evaluating risk or selecting recommendations.
    """

    def __init__(self):
        self.routing_service = routing_service

    def get_candidate_routes(
        self,
        source: str,
        destination: str,
        mode: str = "drive",
    ) -> Tuple[List[RouteResult], bool, Tuple[float, float], Tuple[float, float]]:
        """
        Geocodes source and destination in parallel, queries Geoapify/OSRM for driving routes,
        validates Hyderabad operational boundaries, and constructs normalized RouteResult domain objects.

        Returns:
            - routes: List of RouteResult
            - alternatives_available: bool (False if only 1 physical route is found)
            - origin_coords: (lat, lng)
            - dest_coords: (lat, lng)
        """
        # 1. Parallel geocoding of source and destination
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_origin = executor.submit(self.routing_service.geocode, source)
            future_dest = executor.submit(self.routing_service.geocode, destination)
            origin_lat, origin_lng, origin_name = future_origin.result()
            dest_lat, dest_lng, dest_name = future_dest.result()

        # 2. Validate operational region: Hyderabad Metropolitan Area
        if not is_within_hyderabad_metro(origin_lat, origin_lng) or not is_within_hyderabad_metro(dest_lat, dest_lng):
            raise ValueError("This prototype currently supports emergency routing within Hyderabad.")

        # 3. Fetch driving candidate routes from Geoapify / OSRM
        raw_routes = self.routing_service.fetch_routes(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            mode=mode,
            alternatives=True,
        )

        routes_count = len(raw_routes)
        alternatives_available = routes_count > 1

        # 3. Transform raw routing data into RouteResult domain models
        route_results: List[RouteResult] = []

        for idx, raw_route in enumerate(raw_routes):
            letter = ROUTE_LETTERS[idx] if idx < len(ROUTE_LETTERS) else f"R{idx+1}"
            color = ROUTE_COLOR_PALETTE[idx % len(ROUTE_COLOR_PALETTE)]

            # Distance in meters -> km; duration in seconds -> minutes
            distance_meters = float(raw_route.get("distance", 0.0))
            duration_seconds = float(raw_route.get("duration", 0.0))
            distance_km = round(distance_meters / 1000.0, 1)
            eta_minutes = max(1, round(duration_seconds / 60.0))

            # Extract coordinates in Leaflet [lat, lng] format
            lat_lng_coordinates = raw_route.get("lat_lng_coordinates", [])
            if not lat_lng_coordinates:
                geometry = raw_route.get("geometry", {})
                raw_coords = geometry.get("coordinates", [])
                lat_lng_coordinates = [[float(coord[1]), float(coord[0])] for coord in raw_coords if len(coord) >= 2]

            if not lat_lng_coordinates:
                lat_lng_coordinates = [[origin_lat, origin_lng], [dest_lat, dest_lng]]

            # Extract road name summary
            road_name = raw_route.get("road_name", "").strip()
            if not road_name:
                road_name = f"Corridor via Waypoint {letter}"

            provider = raw_route.get("provider", "Geoapify")
            data_source = raw_route.get("data_source", "geoapify")
            traffic_status = raw_route.get("traffic_status")          # None for Geoapify/OSRM
            traffic_delay_minutes = raw_route.get("traffic_delay_minutes")  # None for Geoapify/OSRM
            route_id = f"route-{letter.lower()}"

            # Build explanation points — mention traffic-aware ETA when available from HERE
            explanation_pts = [
                f"✓ Physical corridor geometry extracted via {provider} ({len(lat_lng_coordinates)} waypoints)",
                f"✓ Total corridor distance: {distance_km} km",
            ]
            if data_source == "here_live" and traffic_status is not None:
                explanation_pts.append(
                    f"✓ Traffic-aware ETA: {eta_minutes} minutes (current traffic: {traffic_status})"
                )
                if traffic_delay_minutes is not None:
                    if traffic_delay_minutes > 0:
                        explanation_pts.append(
                            f"✓ Traffic delay vs. typical: +{traffic_delay_minutes} min"
                        )
                    elif traffic_delay_minutes < 0:
                        explanation_pts.append(
                            f"✓ Lighter-than-typical traffic: {abs(traffic_delay_minutes)} min faster"
                        )
            else:
                explanation_pts.append(f"✓ Nominal travel time: {eta_minutes} minutes")
            explanation_pts.append(f"✓ Key road segments: {road_name}")

            tradeoff = (
                f"Traffic-aware corridor {letter} ({distance_km} km, {eta_minutes} min"
                + (f", traffic: {traffic_status}" if traffic_status else "")
                + ")."
            )

            route_obj = RouteResult(
                id=route_id,
                code=f"Route {letter}",
                name=road_name,
                eta_minutes=eta_minutes,
                distance_km=distance_km,
                risk_percent=0,  # Risk evaluated later by RiskEngine
                status="LOW",
                is_recommended=False,  # Recommendation decided strictly by OptimizerAgent
                reliability_score=0.85,
                confidence_score=95,
                color=color,
                data_source=data_source,
                traffic_status=traffic_status,
                traffic_delay_minutes=traffic_delay_minutes,
                risk_factors=RiskFactors(
                    traffic=0.0,
                    weather=0.0,
                    incident=0.0,
                    road=0.0,
                    overall_risk=0.0,
                ),
                tradeoff_summary=tradeoff,
                explanation_points=explanation_pts,
                coordinates=lat_lng_coordinates,
            )
            route_results.append(route_obj)

        return route_results, alternatives_available, (origin_lat, origin_lng), (dest_lat, dest_lng)


# Singleton instance
route_agent = RouteAgent()
