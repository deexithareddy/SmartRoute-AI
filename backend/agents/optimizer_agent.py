"""
Optimizer Agent

Scores every candidate route on ETA + risk + predicted delay + reliability,
weighted differently per vehicle type and mission priority, and picks the best one.
Integrates ML Delay Prediction with hybrid fallback.
"""

from typing import Dict, List, Optional, Tuple
from backend.models.schemas import RouteResult
from backend.engine.scoring import scoring_engine
from backend.ml.predictor import delay_predictor, DelayFeatureInput


class OptimizerAgent:
    """
    Route optimization agent that performs multi-criteria ranking
    tailored to specific emergency vehicle mission profiles.
    """

    def __init__(self):
        self.scoring_engine = scoring_engine
        self.delay_predictor = delay_predictor

    def estimate_route_reliability(
        self, traffic_risk: float, incident_risk: float, weather_risk: float, road_risk: float
    ) -> float:
        """
        Calculates route arrival certainty (0.0 to 1.0) based on stability across factors.
        """
        volatility_penalty = (
            0.40 * traffic_risk
            + 0.35 * incident_risk
            + 0.15 * weather_risk
            + 0.10 * road_risk
        )
        reliability = max(0.20, min(0.98, 1.0 - volatility_penalty))
        return round(reliability, 2)

    def optimize_routes(
        self,
        routes: List[RouteResult],
        vehicle_type: str = "Ambulance",
        priority: str = "Critical",
        traffic_telemetry_available: bool = True,
        weather_telemetry_available: bool = True,
    ) -> Tuple[List[RouteResult], Optional[RouteResult]]:
        """
        Evaluates and ranks candidate routes based on vehicle mission weights
        and ML-predicted / rule-fallback transit delays.
        """
        if not routes:
            return [], None

        # 1. Retrieve named weights for the requested vehicle type
        weights = self.scoring_engine.get_weights_for_vehicle(vehicle_type)

        priority_lower = (priority or "").lower()
        if "critical" in priority_lower and "ambulance" in (vehicle_type or "").lower():
            # In critical code-1 ambulance mission, speed weight Wt is even higher
            weights = {
                "wt": min(0.60, weights["wt"] + 0.10),
                "wr": max(0.20, weights["wr"] - 0.05),
                "wd": weights["wd"],
                "wl": max(0.05, weights["wl"] - 0.05),
            }

        all_etas = [float(r.eta_minutes) for r in routes]
        scored_routes: List[RouteResult] = []

        for route in routes:
            traffic_risk = float(route.risk_factors.traffic)
            weather_risk = float(route.risk_factors.weather)
            incident_risk = float(route.risk_factors.incident)
            road_risk = float(route.risk_factors.road)
            overall_risk = float(route.risk_factors.overall_risk)

            # Determine baseline free-flow speed based on road class
            name_lower = route.name.lower()
            if any(kw in name_lower for kw in ["expressway", "flyover", "elevated", "bypass"]):
                expected_speed = 75.0
            elif any(kw in name_lower for kw in ["arterial", "main road", "avenue", "ring road"]):
                expected_speed = 48.0
            else:
                expected_speed = 32.0

            observed_speed = max(5.0, round(expected_speed * max(0.15, 1.0 - traffic_risk * 0.85), 1))

            # 2. Run Hybrid ML Delay Prediction
            feature_input = DelayFeatureInput(
                observed_speed_kmh=observed_speed if traffic_telemetry_available else None,
                expected_speed_kmh=expected_speed,
                baseline_duration_minutes=float(route.eta_minutes),
                rainfall_mm=round(weather_risk * 35.0, 1) if weather_telemetry_available else None,
                visibility_m=max(400.0, 10000.0 - weather_risk * 7500.0),
                wind_speed_kmh=12.0 + weather_risk * 30.0,
                incident_count=1 if incident_risk > 0.15 else 0,
                incident_severity=incident_risk,
                road_name=route.name,
                traffic_available=traffic_telemetry_available,
                weather_available=weather_telemetry_available,
            )

            delay_result = self.delay_predictor.predict_delay(feature_input)
            delay_minutes = delay_result.predicted_delay_minutes

            # 3. Compute route reliability
            reliability = self.estimate_route_reliability(
                traffic_risk=traffic_risk,
                incident_risk=incident_risk,
                weather_risk=weather_risk,
                road_risk=road_risk,
            )

            # 4. Normalize criteria to 0.0 - 1.0 penalty scales
            eta_score = self.scoring_engine.normalize_eta(route.eta_minutes, all_etas)
            delay_score = self.scoring_engine.normalize_delay(delay_minutes, route.eta_minutes)

            # 5. Compute composite Route Score (lower is better)
            route_score = self.scoring_engine.compute_route_score(
                eta_score=eta_score,
                risk_score=overall_risk,
                delay_score=delay_score,
                reliability=reliability,
                weights=weights,
            )

            # 6. Attach metrics to route result
            route.overall_score = route_score
            route.reliability_score = reliability
            route.predicted_delay_minutes = delay_minutes
            route.delay_prediction_source = delay_result.source

            # Insert ML/Rule-based delay explanation point
            route.explanation_points.insert(0, delay_result.explanation)

            # Vehicle-tailored trade-off explanation
            route.tradeoff_summary = (
                f"Mission Profile ({vehicle_type} - {priority}): Score {route_score:.3f} "
                f"(ETA: {route.eta_minutes}m, Risk: {route.risk_percent}%, Delay: +{delay_minutes}m [{delay_result.source.upper()}], Reliability: {Math_pct(reliability)}%)."
            )

            scored_routes.append(route)

        # 7. Rank routes by composite score (lowest score first = BEST)
        ranked_routes = sorted(scored_routes, key=lambda r: r.overall_score)

        # 8. Flag top-scoring candidate as recommended
        for idx, r in enumerate(ranked_routes):
            if idx == 0:
                r.is_recommended = True
                r.status = "BEST"
            else:
                r.is_recommended = False
                from backend.engine.risk_engine import risk_engine
                r.status = risk_engine.map_risk_to_label(r.risk_factors.overall_risk)

        recommended_route = ranked_routes[0] if ranked_routes else None

        return ranked_routes, recommended_route


def Math_pct(val: float) -> str:
    """Helper formatting float to percentage string."""
    return f"{int(round(val * 100))}"


# Singleton instance
optimizer_agent = OptimizerAgent()
