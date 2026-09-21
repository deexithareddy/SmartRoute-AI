"""
News & Incident Agent

Processes news alerts and CAD incident reports through a spatial relevance pipeline:
  raw text -> event classification -> location extraction -> route geometry relevance check -> severity scoring

Only attaches an incident to a route if its location genuinely intersects that route's path.
If no incidents exist for a route, incident_risk = 0.0.
If the news feed is offline, explicitly flags data_available: false.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from backend.services.news_service import news_service, IncidentItem

# ==============================================================================
# Configurable Proximity & Severity Constants
# ==============================================================================

MAX_PROXIMITY_BUFFER_KM = 1.2  # Max distance from route polyline to consider incident affecting the route

# Severity Risk Scores
SEVERITY_SCORE_MAP = {
    "high": 0.75,
    "critical": 0.85,
    "medium": 0.40,
    "low": 0.20,
}


@dataclass
class MatchedIncident:
    """Incident report matched to a specific candidate route."""
    incident_id: str
    headline: str
    event_type: str
    severity: str
    location_name: str
    min_distance_km: float
    risk_score: float
    reported_time: str
    lat: float = 0.0
    lng: float = 0.0


@dataclass
class NewsEvaluationResult:
    """Incident evaluation outcome for a specific route corridor."""
    data_available: bool
    incident_risk_score: Optional[float]  # 0.0 to 1.0 (0.0 if clean, None if offline)
    has_incidents: bool
    matched_incidents: List[MatchedIncident] = field(default_factory=list)
    explanation: str = ""


class NewsAgent:
    """
    Incident agent evaluating active hazards along route geometries.
    """

    def __init__(self):
        self.news_service = news_service

    def haversine_distance_km(
        self, lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """Calculates spherical distance between two geographic coordinates in kilometers."""
        R = 6371.0  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def min_distance_to_polyline_km(
        self, point_lat: float, point_lng: float, polyline: List[List[float]]
    ) -> float:
        """Finds the minimum distance from an incident point to any coordinate on the polyline."""
        if not polyline:
            return float("inf")
        return min(
            self.haversine_distance_km(point_lat, point_lng, c[0], c[1]) for c in polyline
        )

    def evaluate_route_incidents(
        self, coordinates: List[List[float]]
    ) -> NewsEvaluationResult:
        """
        Evaluates active incidents against a route's polyline geometry.
        """
        feed_items = self.news_service.fetch_incidents()

        # Failure guard: If news feed is offline, flag data_available: False
        if feed_items is None:
            return NewsEvaluationResult(
                data_available=False,
                incident_risk_score=None,
                has_incidents=False,
                matched_incidents=[],
                explanation="⚠️ Incident intelligence feed offline — route disruption status unverified",
            )

        matched: List[MatchedIncident] = []

        for item in feed_items:
            # Check spatial relevance against the route's polyline
            dist_km = self.min_distance_to_polyline_km(item.lat, item.lng, coordinates)
            buffer = max(MAX_PROXIMITY_BUFFER_KM, item.impact_radius_km)

            if dist_km <= buffer:
                score = SEVERITY_SCORE_MAP.get(item.severity.lower(), 0.35)
                matched.append(
                    MatchedIncident(
                        incident_id=item.incident_id,
                        headline=item.headline,
                        event_type=item.event_type,
                        severity=item.severity,
                        location_name=item.location_name,
                        min_distance_km=round(dist_km, 2),
                        risk_score=score,
                        reported_time=item.reported_time,
                        lat=item.lat,
                        lng=item.lng,
                    )
                )

        if not matched:
            return NewsEvaluationResult(
                data_available=True,
                incident_risk_score=0.0,  # Explicitly 0.0 when clean
                has_incidents=False,
                matched_incidents=[],
                explanation="✓ No reported disruptions, closures, or emergency incidents along corridor",
            )

        # Composite incident risk: take highest severity score + slight buffer for multiple
        max_score = max(m.risk_score for m in matched)
        composite_score = round(min(1.0, max_score + 0.05 * (len(matched) - 1)), 2)

        # Formulate grounded explanation
        primary_incident = matched[0]
        explanation = (
            f"⚠️ Active Incident: {primary_incident.headline} "
            f"(Severity: {primary_incident.severity.upper()}, {primary_incident.min_distance_km}km from path)"
        )

        return NewsEvaluationResult(
            data_available=True,
            incident_risk_score=composite_score,
            has_incidents=True,
            matched_incidents=matched,
            explanation=explanation,
        )


# Singleton instance
news_agent = NewsAgent()
