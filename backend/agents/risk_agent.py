"""
Risk Agent

Agent wrapper that evaluates multi-factor composite risk across
traffic, weather, incident, and road infrastructure factors.
"""

from typing import Dict, List, Optional, Tuple
from backend.models.schemas import RiskFactors, RouteResult
from backend.engine.risk_engine import risk_engine, RiskEngine


class RiskAgent:
    """
    Evaluates multi-factor risk for candidate emergency routes.
    """

    def __init__(self):
        self.engine = risk_engine

    def compute_composite_risk(
        self,
        traffic_risk: float,
        weather_risk: float,
        incident_risk: float,
        road_risk: float,
    ) -> float:
        """Computes normalized overall composite risk score (0.0 to 1.0)."""
        return self.engine.compute_overall_risk(
            traffic_risk=traffic_risk,
            weather_risk=weather_risk,
            incident_risk=incident_risk,
            road_risk=road_risk,
        )

    def evaluate_route(
        self,
        route: RouteResult,
        traffic_risk: float,
        weather_risk: float,
        incident_risk: float,
        road_name: Optional[str] = None,
    ) -> RouteResult:
        """Attaches computed risk factors and composite scores to a route result."""
        road_risk = self.engine.estimate_road_risk(road_name or route.name)
        overall_risk = self.engine.compute_overall_risk(
            traffic_risk=traffic_risk,
            weather_risk=weather_risk,
            incident_risk=incident_risk,
            road_risk=road_risk,
        )
        risk_pct = int(round(overall_risk * 100))
        label = self.engine.map_risk_to_label(overall_risk)

        route.risk_percent = risk_pct
        route.status = label
        route.risk_factors = RiskFactors(
            traffic=traffic_risk,
            weather=weather_risk,
            incident=incident_risk,
            road=road_risk,
            overall_risk=overall_risk,
        )
        return route


# Singleton instance
risk_agent = RiskAgent()
