"""
Simulation Agent

Performs what-if stress-testing simulations on candidate routes under hypothetical
environmental conditions (rainfall surge, traffic multiplier, road closure).
Maintains strict data isolation without mutating live baseline telemetry feeds.
"""

from typing import List, Optional, Tuple
from backend.models.schemas import (
    RouteResult,
    RiskFactors,
    SimulateRequest,
    SimulateResponse,
    SimulatedRouteComparison,
)
from backend.agents.weather_agent import weather_agent
from backend.agents.optimizer_agent import optimizer_agent
from backend.engine.risk_engine import risk_engine


class SimulationAgent:
    """
    Simulation agent evaluating what-if scenarios on emergency corridors.
    """

    def run_simulation(
        self,
        baseline_routes: List[RouteResult],
        request: SimulateRequest,
        origin_coords: Optional[List[float]] = None,
        dest_coords: Optional[List[float]] = None,
    ) -> SimulateResponse:
        """
        Runs scenario simulation on an isolated deep copy of baseline routes.
        """
        if not baseline_routes:
            return SimulateResponse(
                baseline_recommended_route="none",
                simulated_recommended_route="none",
                recommendation_flipped=False,
                comparison=[],
                routes=[],
                explanation=["No candidate routes provided for simulation."],
            )

        # 1. Baseline winner identification
        baseline_winner = next(
            (r for r in baseline_routes if r.is_recommended), baseline_routes[0]
        )
        baseline_recommended_id = baseline_winner.id

        # 2. Create isolated deep copy of all candidate routes
        simulated_routes: List[RouteResult] = [
            r.model_copy(deep=True) for r in baseline_routes
        ]

        # 3. Determine simulated weather score from hypothetical rainfall
        if request.rainfall > 0.0:
            sim_weather_score, _, weather_desc = weather_agent._classify_weather_risk(
                max_rain_mm=request.rainfall,
                max_wind_kmh=18.0 + min(65.0, request.rainfall * 0.9),
                min_visibility_m=max(250.0, 10000.0 - request.rainfall * 140.0),
                has_storm=request.rainfall >= 25.0,
                condition_desc="Simulated Precipitation Surge",
            )
        else:
            sim_weather_score = None  # Retain existing baseline weather

        comparison_list: List[SimulatedRouteComparison] = []
        passable_routes: List[RouteResult] = []

        # 4. Apply hypothetical transformations per route
        for idx, route in enumerate(simulated_routes):
            base_r = baseline_routes[idx]
            is_passable = True

            # (a) Weather transformation
            w_score = (
                sim_weather_score
                if sim_weather_score is not None
                else float(route.risk_factors.weather)
            )
            route.risk_factors.weather = w_score

            # (b) Traffic transformation
            scaled_traffic = min(
                1.0, float(base_r.risk_factors.traffic) * float(request.traffic_multiplier)
            )
            route.risk_factors.traffic = round(scaled_traffic, 2)

            # ETA scaling from traffic congestion
            traffic_delay_factor = (request.traffic_multiplier - 1.0) * 0.50
            sim_eta = int(round(base_r.eta_minutes * (1.0 + max(0.0, traffic_delay_factor))))
            route.eta_minutes = sim_eta

            # (c) Road closure transformation
            # If road closure is activated, mark Route A (or primary arterial) impassable
            if request.road_closure and (
                route.id == "route-a"
                or idx == 0
                or "arterial" in route.name.lower()
                or "whitefield road" in route.name.lower()
            ):
                is_passable = False
                route.status = "CRITICAL"
                route.risk_factors.incident = 1.00
                route.risk_factors.overall_risk = 1.00
                route.risk_percent = 100
                route.overall_score = 9.99
                route.is_recommended = False
                route.explanation_points.insert(
                    0, "⛔ IMPASSABLE: Corridor blocked by simulated road closure & hazard"
                )
                route.tradeoff_summary = (
                    "CRITICAL / CLOSED: Road closure flag renders this corridor completely impassable."
                )
            else:
                # Re-compute composite overall risk: 0.35T + 0.25W + 0.25I + 0.15R
                overall = risk_engine.compute_overall_risk(
                    traffic_risk=route.risk_factors.traffic,
                    weather_risk=route.risk_factors.weather,
                    incident_risk=route.risk_factors.incident,
                    road_risk=route.risk_factors.road,
                )
                route.risk_factors.overall_risk = overall
                route.risk_percent = int(round(overall * 100))
                route.status = risk_engine.map_risk_to_label(overall)
                passable_routes.append(route)

        # 5. Re-run OptimizerAgent on passable routes
        if passable_routes:
            ranked_passable, sim_winner = optimizer_agent.optimize_routes(
                routes=passable_routes,
                vehicle_type=request.vehicle_type or "Ambulance",
                priority=request.priority or "Critical",
            )
            simulated_recommended_id = sim_winner.id if sim_winner else passable_routes[0].id
        else:
            simulated_recommended_id = simulated_routes[0].id

        # 6. Re-assemble comparison list and final route array
        final_sim_routes: List[RouteResult] = []
        for idx, route in enumerate(simulated_routes):
            base_r = baseline_routes[idx]
            is_closed = route.status == "CRITICAL" or route.risk_percent == 100
            is_rec_sim = (route.id == simulated_recommended_id) and not is_closed

            if is_closed:
                route.is_recommended = False
                route.is_passable = False
                route.status = "CRITICAL"
                if "closed" not in route.name.lower():
                    route.name = f"{route.name} (Closed)"
            elif is_rec_sim:
                route.is_recommended = True
                route.is_passable = True
                route.status = "BEST"
            else:
                route.is_recommended = False
                route.is_passable = True

            comparison_list.append(
                SimulatedRouteComparison(
                    id=route.id,
                    code=route.code,
                    name=route.name,
                    current_risk_percent=base_r.risk_percent,
                    simulated_risk_percent=route.risk_percent,
                    current_eta_minutes=base_r.eta_minutes,
                    simulated_eta_minutes=route.eta_minutes,
                    current_status=base_r.status,
                    simulated_status=route.status,
                    is_baseline_recommended=base_r.is_recommended,
                    is_simulated_recommended=is_rec_sim,
                    is_passable=not is_closed,
                )
            )
            final_sim_routes.append(route)

        # 7. Check if recommendation flipped
        recommendation_flipped = baseline_recommended_id != simulated_recommended_id

        # 8. Generate simulation impact narrative
        explanation: List[str] = [
            f"🧪 What-If Simulation: Rainfall {request.rainfall}mm | Traffic {request.traffic_multiplier:.1f}x | Closure: {'YES' if request.road_closure else 'NO'}",
        ]
        if recommendation_flipped:
            explanation.append(
                f"🔄 RECOMMENDATION FLIPPED: Primary recommendation shifted from {baseline_winner.code} to {simulated_recommended_id} due to scenario hazards."
            )
        else:
            explanation.append(
                f"✓ Recommendation maintained on {simulated_recommended_id} despite simulated stress factors."
            )

        if request.road_closure:
            explanation.append("⛔ Road closure isolated to primary arterial corridor.")

        return SimulateResponse(
            baseline_recommended_route=baseline_recommended_id,
            simulated_recommended_route=simulated_recommended_id,
            recommendation_flipped=recommendation_flipped,
            comparison=comparison_list,
            routes=final_sim_routes,
            confidence=0.94,
            confidence_label="HIGH",
            confidence_percent=94,
            explanation=explanation,
            origin_coords=origin_coords or [12.9716, 77.5946],
            destination_coords=dest_coords or [12.9352, 77.6245],
        )


# Singleton instance
simulation_agent = SimulationAgent()
