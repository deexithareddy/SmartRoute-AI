"""
SmartRoute AI - SIH Demo Service

Provides 7 standardized, repeatable demonstration scenarios for SIH jury presentations:
  1. SCENARIO 1 — Normal Conditions
  2. SCENARIO 2 — Severe Traffic Anomaly (Cause: UNKNOWN)
  3. SCENARIO 3 — Heavy Rainfall (45 mm/h weather exposure)
  4. SCENARIO 4 — Confirmed Road Incident (CAD dispatch confirmed on corridor)
  5. SCENARIO 5 — Road Closure (Arterial closed, surviving bypass)
  6. SCENARIO 6 — Traffic Data Unavailable (Graceful degradation, 75% confidence)
  7. SCENARIO 7 — Only One Route Available (Single route honest guard)

Produces deterministic outputs labeled as DEMO DATA without altering live pipeline code.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.models.schemas import (
    AnalyzeResponse,
    RouteResult,
    RiskFactors,
    IncidentDTO,
    MissionProfileDTO,
    DemoScenarioInfo,
)
from backend.engine.scoring import scoring_engine

DEMO_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "scenario_1",
        "number": 1,
        "name": "SCENARIO 1 — Normal Conditions",
        "short_title": "1. Normal Conditions",
        "icon": "🟢",
        "description": "Clear weather, smooth free-flow traffic, zero reported incidents across all corridors.",
        "expected_recommended_route": "Route A (Direct Arterial)",
        "expected_confidence_label": "HIGH (95%)",
        "key_features": [
            "All 4 telemetry feeds LIVE",
            "Route A is fastest (16 min) and recommended",
            "Low risk profile (14% composite risk)",
            "Zero anomalies or hazards",
        ],
    },
    {
        "id": "scenario_2",
        "number": 2,
        "name": "SCENARIO 2 — Severe Traffic Anomaly",
        "short_title": "2. Severe Traffic Anomaly",
        "icon": "🔴",
        "description": "Sudden speed collapse on Route A (12 km/h vs 45 km/h expected). Cause is strictly UNKNOWN.",
        "expected_recommended_route": "Route B (Varthur Bypass)",
        "expected_confidence_label": "HIGH (95%)",
        "key_features": [
            "Speed ratio collapses to 0.27 on Route A",
            "Cause labeled UNKNOWN (No CAD confirmation)",
            "Recommendation flips to Route B",
            "ML delay prediction on Route A surges to +16.5 min",
        ],
    },
    {
        "id": "scenario_3",
        "number": 3,
        "name": "SCENARIO 3 — Heavy Rainfall & Storm",
        "short_title": "3. Heavy Rainfall",
        "icon": "🌧️",
        "description": "Torrential monsoon downpour (45 mm/h rain, 52 km/h wind, 800m visibility) threatening low underpasses.",
        "expected_recommended_route": "Route B (Elevated Corridor)",
        "expected_confidence_label": "HIGH (95%)",
        "key_features": [
            "Open-Meteo Doppler precipitation surge (45 mm/h)",
            "Route A penalized for low-lying waterlogging",
            "Route B Elevated Expressway recommended for drainage resilience",
            "92% arrival reliability on Route B",
        ],
    },
    {
        "id": "scenario_4",
        "number": 4,
        "name": "SCENARIO 4 — Confirmed Road Incident",
        "short_title": "4. Confirmed CAD Incident",
        "icon": "🚨",
        "description": "CAD emergency dispatch confirms multi-vehicle collision blocking eastbound lanes on Route A.",
        "expected_recommended_route": "Route B (Varthur Bypass)",
        "expected_confidence_label": "HIGH (95%)",
        "key_features": [
            "Active CAD incident marker placed on Route A map",
            "Traffic anomaly cause confirmed: 'Multi-Vehicle Collision'",
            "Incident impact radius 1.2 km",
            "Route B safely circumvents hazard",
        ],
    },
    {
        "id": "scenario_5",
        "number": 5,
        "name": "SCENARIO 5 — Road Closure & Invalidation",
        "short_title": "5. Road Closure",
        "icon": "⛔",
        "description": "Physical road closure on Route A due to underpass flooding. Corridor is visually marked CLOSED.",
        "expected_recommended_route": "Route B (Surviving Corridor)",
        "expected_confidence_label": "HIGH (95%)",
        "key_features": [
            "Route A isPassable: false (Visual CLOSED status)",
            "Optimizer excludes closed route from ranking",
            "Route B selected as sole viable emergency path",
            "Side-by-side comparison highlights impassable status",
        ],
    },
    {
        "id": "scenario_6",
        "number": 6,
        "name": "SCENARIO 6 — Traffic Data Unavailable",
        "short_title": "6. Traffic Offline (Degradation)",
        "icon": "⚡",
        "description": "Municipal traffic sensor feed drops offline. System gracefully degrades and reduces confidence.",
        "expected_recommended_route": "Route A (Deterministic Fallback)",
        "expected_confidence_label": "MODERATE (75%)",
        "key_features": [
            "Traffic feed status marked UNAVAILABLE",
            "Confidence score reduces from 95% to 75%",
            "Delay predictor switches to ⚙️ Rule-Based Heuristics",
            "Explanation honestly warns: 'Traffic telemetry unavailable'",
        ],
    },
    {
        "id": "scenario_7",
        "number": 7,
        "name": "SCENARIO 7 — Only One Route Available",
        "short_title": "7. Single Route Guard",
        "icon": "🛣️",
        "description": "Topographical / road network constraint leaves only a single physical route with zero alternatives.",
        "expected_recommended_route": "Route A (Single Viable Route)",
        "expected_confidence_label": "HIGH (95%)",
        "key_features": [
            "alternatives_available: false",
            "Honest banner: 'Only one viable route found. No alternative available.'",
            "Zero fabricated Route B/C dummy corridors",
            "Single-corridor mathematical evaluation",
        ],
    },
]


class DemoService:
    """
    Coordinator for repeatable SIH presentation scenarios.
    Returns deterministic, mathematically consistent responses labeled as DEMO DATA.
    """

    def __init__(self):
        self.active_scenario_id: Optional[str] = None

    def get_scenarios(self) -> List[DemoScenarioInfo]:
        """Returns the catalog of 7 standardized SIH demo scenarios."""
        return [
            DemoScenarioInfo(
                id=s["id"],
                number=s["number"],
                name=s["name"],
                short_title=s["short_title"],
                description=s["description"],
                icon=s["icon"],
                expected_recommended_route=s["expected_recommended_route"],
                expected_confidence_label=s["expected_confidence_label"],
                key_features=s["key_features"],
            )
            for s in DEMO_SCENARIOS
        ]

    def get_active_scenario(self) -> Optional[str]:
        return self.active_scenario_id

    def reset_demo_mode(self) -> None:
        self.active_scenario_id = None

    def generate_scenario_response(
        self,
        scenario_id: str,
        vehicle_type: str = "Ambulance",
        priority: str = "Critical",
    ) -> Tuple[AnalyzeResponse, str]:
        """
        Builds a deterministic AnalyzeResponse for the specified demo scenario.
        """
        self.active_scenario_id = scenario_id
        profile_data = scoring_engine.get_profile_details(vehicle_type, priority)
        profile_dto = MissionProfileDTO(**profile_data)

        origin_coords = [12.9719, 77.6412]  # Indiranagar
        dest_coords = [12.9698, 77.7500]    # Whitefield

        # Coordinates geometries
        coords_a = [
            [12.9719, 77.6412],
            [12.9740, 77.6650],
            [12.9720, 77.7000],
            [12.9705, 77.7280],
            [12.9698, 77.7500],
        ]
        coords_b = [
            [12.9719, 77.6412],
            [12.9550, 77.6600],
            [12.9480, 77.7100],
            [12.9590, 77.7380],
            [12.9698, 77.7500],
        ]

        if scenario_id == "scenario_1":
            # SCENARIO 1: Normal Conditions
            route_a = RouteResult(
                id="route-a",
                code="Route A",
                name="Direct Arterial (Old Madras / Whitefield Rd)",
                eta_minutes=16,
                distance_km=11.2,
                risk_percent=14,
                status="LOW",
                is_recommended=True,
                reliability_score=0.94,
                confidence_score=95,
                color="#10b981",
                risk_factors=RiskFactors(traffic=0.12, weather=0.10, incident=0.0, road=0.15, overall_risk=0.14),
                overall_score=0.12,
                predicted_delay_minutes=0.8,
                delay_prediction_source="ml",
                explanation_points=[
                    "✓ Optimal travel corridor: Fastest arrival time (16 min ETA)",
                    "✓ Free-flow traffic telemetry (Observed speed 48 km/h vs expected 50 km/h)",
                    "✓ Clear atmospheric conditions with zero precipitation",
                    "✓ Zero reported CAD incidents or lane closures",
                ],
                tradeoff_summary="Fastest and safest path under baseline clear conditions with lowest risk score.",
                coordinates=coords_a,
                is_passable=True,
            )
            route_b = RouteResult(
                id="route-b",
                code="Route B",
                name="Elevated Bypass (Varthur Outer Link)",
                eta_minutes=19,
                distance_km=13.8,
                risk_percent=18,
                status="LOW",
                is_recommended=False,
                reliability_score=0.91,
                confidence_score=95,
                color="#38bdf8",
                risk_factors=RiskFactors(traffic=0.15, weather=0.12, incident=0.0, road=0.20, overall_risk=0.18),
                overall_score=0.19,
                predicted_delay_minutes=1.2,
                delay_prediction_source="ml",
                explanation_points=[
                    "• +3 minutes slower than Route A (19 min vs 16 min ETA)",
                    "✓ Reliable secondary bypass corridor with open shoulders",
                    "✓ Free-flow traffic conditions",
                ],
                tradeoff_summary="Viable secondary alternative, slightly longer transit distance.",
                coordinates=coords_b,
                is_passable=True,
            )
            resp = AnalyzeResponse(
                recommended_route="route-a",
                routes=[route_a, route_b],
                confidence=0.95,
                confidence_label="HIGH",
                confidence_percent=95,
                explanation=[
                    "Route A recommended because:",
                    "• Fastest candidate route (16 min ETA)",
                    "• Lowest combined multi-factor risk score (14%)",
                    "• Smooth traffic flow with zero reported incidents",
                    "Route B not selected because:",
                    "• +3 minutes slower than primary arterial",
                ],
                alternatives_available=True,
                origin_coords=origin_coords,
                destination_coords=dest_coords,
                incidents=[],
                optimization_profile=profile_dto,
                pipeline_timings_ms={"total_analyze_ms": 2.8, "sensor_ingestion_ms": 1.4},
            )
            return resp, "SCENARIO 1 — Normal Conditions Activated (DEMO DATA)"

        elif scenario_id == "scenario_2":
            # SCENARIO 2: Severe Traffic Anomaly
            route_a = RouteResult(
                id="route-a",
                code="Route A",
                name="Direct Arterial (Old Madras Rd)",
                eta_minutes=29,
                distance_km=11.2,
                risk_percent=48,
                status="MODERATE",
                is_recommended=False,
                reliability_score=0.46,
                confidence_score=95,
                color="#f59e0b",
                risk_factors=RiskFactors(traffic=0.78, weather=0.10, incident=0.0, road=0.20, overall_risk=0.48),
                overall_score=0.46,
                predicted_delay_minutes=16.5,
                delay_prediction_source="ml",
                explanation_points=[
                    "⚠️ Severe traffic anomaly detected: Observed speed 12.0 km/h vs expected 45.0 km/h (speed ratio 0.27)",
                    "⚠️ Anomaly Cause: UNKNOWN (Unconfirmed by police or CAD incident feed)",
                    "⚠️ Predicted transit delay +16.5 minutes over baseline",
                ],
                tradeoff_summary="Severe congestion anomaly causes high delay risk (+16.5m) and low arrival certainty.",
                coordinates=coords_a,
                is_passable=True,
                traffic_anomaly={
                    "has_anomaly": True,
                    "severity": "SEVERE",
                    "observed_speed": 12.0,
                    "expected_speed": 45.0,
                    "speed_ratio": 0.27,
                    "cause": "UNKNOWN",
                    "explanation": "⚠️ Traffic anomaly detected: Observed speed 12.0 km/h vs expected 45.0 km/h (Cause: UNKNOWN)",
                    "coordinate": coords_a[2],
                },
            )
            route_b = RouteResult(
                id="route-b",
                code="Route B",
                name="Elevated Bypass (Varthur Outer Link)",
                eta_minutes=19,
                distance_km=13.8,
                risk_percent=18,
                status="LOW",
                is_recommended=True,
                reliability_score=0.91,
                confidence_score=95,
                color="#10b981",
                risk_factors=RiskFactors(traffic=0.15, weather=0.12, incident=0.0, road=0.20, overall_risk=0.18),
                overall_score=0.18,
                predicted_delay_minutes=1.2,
                delay_prediction_source="ml",
                explanation_points=[
                    "✓ Optimal route choice: 10 minutes FASTER than congested Route A under current bottleneck",
                    "✓ 63% lower traffic congestion risk than Route A",
                    "✓ High arrival reliability (91%)",
                ],
                tradeoff_summary="Bypasses severe arterial congestion with predictable transit time.",
                coordinates=coords_b,
                is_passable=True,
            )
            resp = AnalyzeResponse(
                recommended_route="route-b",
                routes=[route_b, route_a],
                confidence=0.95,
                confidence_label="HIGH",
                confidence_percent=95,
                explanation=[
                    "Route B recommended because:",
                    "• 10 minutes faster than congested arterial (19 min vs 29 min ETA)",
                    "• 63% lower traffic risk with predictable flow",
                    "Route A not selected because:",
                    "• Severe traffic anomaly detected (Speed ratio 0.27, Cause: UNKNOWN)",
                    "• +16.5 minutes predicted transit delay",
                ],
                alternatives_available=True,
                origin_coords=origin_coords,
                destination_coords=dest_coords,
                incidents=[],
                optimization_profile=profile_dto,
                pipeline_timings_ms={"total_analyze_ms": 3.1, "sensor_ingestion_ms": 1.6},
            )
            return resp, "SCENARIO 2 — Severe Traffic Anomaly Activated (DEMO DATA)"

        elif scenario_id == "scenario_3":
            # SCENARIO 3: Heavy Rainfall
            route_a = RouteResult(
                id="route-a",
                code="Route A",
                name="Direct Arterial (Old Madras Rd)",
                eta_minutes=32,
                distance_km=11.2,
                risk_percent=64,
                status="HIGH",
                is_recommended=False,
                reliability_score=0.38,
                confidence_score=95,
                color="#f59e0b",
                risk_factors=RiskFactors(traffic=0.55, weather=0.78, incident=0.10, road=0.35, overall_risk=0.64),
                overall_score=0.62,
                predicted_delay_minutes=14.2,
                delay_prediction_source="ml",
                explanation_points=[
                    "⛔ High weather hazard: Torrential precipitation 45.0 mm/h with severe waterlogging risk",
                    "⚠️ Visibility reduced to 800m with 52 km/h wind gusts",
                    "⚠️ Underpass flood vulnerability along km 4.2 - 6.8",
                ],
                tradeoff_summary="High waterlogging exposure in low-lying underpasses creates severe delay volatility.",
                coordinates=coords_a,
                is_passable=True,
            )
            route_b = RouteResult(
                id="route-b",
                code="Route B",
                name="Elevated Expressway Corridor",
                eta_minutes=22,
                distance_km=13.8,
                risk_percent=26,
                status="MODERATE",
                is_recommended=True,
                reliability_score=0.88,
                confidence_score=95,
                color="#10b981",
                risk_factors=RiskFactors(traffic=0.22, weather=0.28, incident=0.0, road=0.15, overall_risk=0.26),
                overall_score=0.24,
                predicted_delay_minutes=2.4,
                delay_prediction_source="ml",
                explanation_points=[
                    "✓ Elevated flyover structure avoids low-lying underpass flood bottlenecks",
                    "✓ 50% lower weather risk than surface arterial",
                    "✓ 10 minutes faster than flooded Route A",
                ],
                tradeoff_summary="Elevated grade separates emergency transit from standing surface water.",
                coordinates=coords_b,
                is_passable=True,
            )
            resp = AnalyzeResponse(
                recommended_route="route-b",
                routes=[route_b, route_a],
                confidence=0.95,
                confidence_label="HIGH",
                confidence_percent=95,
                explanation=[
                    "Route B recommended because:",
                    "• Elevated flyover avoids low-lying underpass flooding",
                    "• 10 minutes faster than waterlogged arterial",
                    "• 50% lower weather risk",
                    "Route A not selected because:",
                    "• Severe rainfall exposure (45 mm/h) with flood hazard in underpasses",
                ],
                alternatives_available=True,
                origin_coords=origin_coords,
                destination_coords=dest_coords,
                incidents=[],
                optimization_profile=profile_dto,
                pipeline_timings_ms={"total_analyze_ms": 3.4, "sensor_ingestion_ms": 1.7},
            )
            return resp, "SCENARIO 3 — Heavy Rainfall & Storm Activated (DEMO DATA)"

        elif scenario_id == "scenario_4":
            # SCENARIO 4: Confirmed Road Incident
            inc = IncidentDTO(
                incident_id="CAD-8842",
                headline="Multi-vehicle collision blocking 2 eastbound lanes",
                event_type="accident",
                severity="high",
                location_name="Old Madras Rd near Junction 4",
                lat=coords_a[2][0],
                lng=coords_a[2][1],
                reported_time="4 min ago (CAD Unit 104)",
                affected_route_ids=["route-a"],
            )
            route_a = RouteResult(
                id="route-a",
                code="Route A",
                name="Direct Arterial (Old Madras Rd)",
                eta_minutes=36,
                distance_km=11.2,
                risk_percent=72,
                status="HIGH",
                is_recommended=False,
                reliability_score=0.32,
                confidence_score=95,
                color="#f59e0b",
                risk_factors=RiskFactors(traffic=0.72, weather=0.10, incident=0.85, road=0.25, overall_risk=0.72),
                overall_score=0.71,
                predicted_delay_minutes=18.0,
                delay_prediction_source="ml",
                explanation_points=[
                    "🚨 Active Incident: Multi-vehicle collision blocking 2 eastbound lanes (CAD Verified)",
                    "⚠️ Traffic anomaly confirmed by police incident feed (Observed speed 14.0 km/h vs expected 45.0 km/h)",
                    "⚠️ Severe bottleneck delay (+18.0 min delay risk)",
                ],
                tradeoff_summary="Active emergency collision creates severe obstruction on primary lane.",
                coordinates=coords_a,
                is_passable=True,
                incidents=[inc],
                traffic_anomaly={
                    "has_anomaly": True,
                    "severity": "SEVERE",
                    "observed_speed": 14.0,
                    "expected_speed": 45.0,
                    "speed_ratio": 0.31,
                    "cause": "Multi-vehicle collision blocking 2 eastbound lanes",
                    "explanation": "⚠️ Traffic anomaly confirmed by CAD incident feed: Multi-vehicle collision",
                    "coordinate": coords_a[2],
                },
            )
            route_b = RouteResult(
                id="route-b",
                code="Route B",
                name="Elevated Bypass (Varthur Outer Link)",
                eta_minutes=19,
                distance_km=13.8,
                risk_percent=18,
                status="LOW",
                is_recommended=True,
                reliability_score=0.91,
                confidence_score=95,
                color="#10b981",
                risk_factors=RiskFactors(traffic=0.15, weather=0.12, incident=0.0, road=0.20, overall_risk=0.18),
                overall_score=0.18,
                predicted_delay_minutes=1.2,
                delay_prediction_source="ml",
                explanation_points=[
                    "✓ 17 minutes faster than incident-blocked Route A",
                    "✓ Zero emergency incidents on peripheral corridor",
                    "✓ 91% arrival reliability",
                ],
                tradeoff_summary="Clear bypass completely circumvents active police accident scene.",
                coordinates=coords_b,
                is_passable=True,
            )
            resp = AnalyzeResponse(
                recommended_route="route-b",
                routes=[route_b, route_a],
                confidence=0.95,
                confidence_label="HIGH",
                confidence_percent=95,
                explanation=[
                    "Route B recommended because:",
                    "• 17 minutes faster than incident-blocked arterial",
                    "• Zero incidents on bypass corridor",
                    "Route A not selected because:",
                    "• Active confirmed incident: Multi-vehicle collision blocking 2 lanes",
                    "• +18.0 min predicted delay",
                ],
                alternatives_available=True,
                origin_coords=origin_coords,
                destination_coords=dest_coords,
                incidents=[inc],
                optimization_profile=profile_dto,
                pipeline_timings_ms={"total_analyze_ms": 3.2, "sensor_ingestion_ms": 1.5},
            )
            return resp, "SCENARIO 4 — Confirmed Road Incident Activated (DEMO DATA)"

        elif scenario_id == "scenario_5":
            # SCENARIO 5: Road Closure
            route_a = RouteResult(
                id="route-a",
                code="Route A",
                name="Direct Arterial [CLOSED - Flash Flood Overtopping]",
                eta_minutes=999,
                distance_km=11.2,
                risk_percent=100,
                status="CRITICAL",
                is_recommended=False,
                reliability_score=0.0,
                confidence_score=95,
                color="#e11d48",
                risk_factors=RiskFactors(traffic=1.0, weather=1.0, incident=1.0, road=1.0, overall_risk=1.0),
                overall_score=1.0,
                predicted_delay_minutes=999.0,
                delay_prediction_source="rule_based",
                explanation_points=[
                    "⛔ ROAD CLOSED: Flash flooding overtopping roadway — transit strictly prohibited",
                    "⛔ Impassable corridor excluded from dispatch consideration",
                ],
                tradeoff_summary="IMPASSABLE / CLOSED: Route physically barred due to water overtopping.",
                coordinates=coords_a,
                is_passable=False,
            )
            route_b = RouteResult(
                id="route-b",
                code="Route B",
                name="Elevated Bypass (Varthur Outer Link)",
                eta_minutes=21,
                distance_km=13.8,
                risk_percent=22,
                status="LOW",
                is_recommended=True,
                reliability_score=0.92,
                confidence_score=95,
                color="#10b981",
                risk_factors=RiskFactors(traffic=0.18, weather=0.20, incident=0.0, road=0.20, overall_risk=0.22),
                overall_score=0.21,
                predicted_delay_minutes=1.8,
                delay_prediction_source="ml",
                explanation_points=[
                    "✓ Sole surviving emergency transit corridor",
                    "✓ Fully passable with open shoulders and active drainage",
                    "✓ 21 min ETA to destination trauma center",
                ],
                tradeoff_summary="Sole viable path ensuring emergency vehicle passage.",
                coordinates=coords_b,
                is_passable=True,
            )
            resp = AnalyzeResponse(
                recommended_route="route-b",
                routes=[route_b, route_a],
                confidence=0.95,
                confidence_label="HIGH",
                confidence_percent=95,
                explanation=[
                    "Route B recommended because:",
                    "• Sole surviving passable corridor to trauma center",
                    "• Wide shoulders and high reliability (92%)",
                    "Route A not selected because:",
                    "• Road closed due to flood overtopping (Impassable)",
                ],
                alternatives_available=True,
                origin_coords=origin_coords,
                destination_coords=dest_coords,
                incidents=[],
                optimization_profile=profile_dto,
                pipeline_timings_ms={"total_analyze_ms": 2.9, "sensor_ingestion_ms": 1.4},
            )
            return resp, "SCENARIO 5 — Road Closure Activated (DEMO DATA)"

        elif scenario_id == "scenario_6":
            # SCENARIO 6: Traffic Data Unavailable
            route_a = RouteResult(
                id="route-a",
                code="Route A",
                name="Direct Arterial (Old Madras Rd)",
                eta_minutes=18,
                distance_km=11.2,
                risk_percent=32,
                status="MODERATE",
                is_recommended=True,
                reliability_score=0.72,
                confidence_score=75,
                color="#10b981",
                risk_factors=RiskFactors(traffic=0.30, weather=0.10, incident=0.0, road=0.20, overall_risk=0.24),
                overall_score=0.25,
                predicted_delay_minutes=2.5,
                delay_prediction_source="rule_based",
                explanation_points=[
                    "⚠️ Traffic telemetry offline — using baseline historical flow risk",
                    "⚙️ Rule-based delay heuristic applied (+2.5 min estimate)",
                    "✓ Weather radar online (Clear conditions)",
                    "✓ Zero CAD incidents reported",
                ],
                tradeoff_summary="Primary corridor selected with moderate confidence due to sensor disconnection.",
                coordinates=coords_a,
                is_passable=True,
            )
            route_b = RouteResult(
                id="route-b",
                code="Route B",
                name="Elevated Bypass (Varthur Link)",
                eta_minutes=22,
                distance_km=13.8,
                risk_percent=35,
                status="MODERATE",
                is_recommended=False,
                reliability_score=0.70,
                confidence_score=75,
                color="#38bdf8",
                risk_factors=RiskFactors(traffic=0.30, weather=0.12, incident=0.0, road=0.25, overall_risk=0.28),
                overall_score=0.31,
                predicted_delay_minutes=3.0,
                delay_prediction_source="rule_based",
                explanation_points=[
                    "⚠️ Traffic telemetry offline",
                    "• +4 min slower than Route A",
                ],
                tradeoff_summary="Secondary alternative evaluated under sensor degradation.",
                coordinates=coords_b,
                is_passable=True,
            )
            resp = AnalyzeResponse(
                recommended_route="route-a",
                routes=[route_a, route_b],
                confidence=0.75,
                confidence_label="MODERATE",
                confidence_percent=75,
                explanation=[
                    "Route A recommended with MODERATE confidence (75%) because:",
                    "• Fastest nominal path (18 min ETA)",
                    "• ⚠️ Traffic data unavailable — confidence reduced to 75%",
                    "• Delay estimated via deterministic rule fallback",
                    "Route B not selected because:",
                    "• Longer nominal transit time",
                ],
                alternatives_available=True,
                origin_coords=origin_coords,
                destination_coords=dest_coords,
                incidents=[],
                optimization_profile=profile_dto,
                pipeline_timings_ms={"total_analyze_ms": 2.5, "sensor_ingestion_ms": 1.2},
            )
            return resp, "SCENARIO 6 — Traffic Data Unavailable Activated (DEMO DATA)"

        else:
            # SCENARIO 7: Only One Route Available
            route_a = RouteResult(
                id="route-a",
                code="Route A",
                name="Single Isolated Mountain Corridor (NH-75 Bridge)",
                eta_minutes=24,
                distance_km=15.4,
                risk_percent=22,
                status="LOW",
                is_recommended=True,
                reliability_score=0.92,
                confidence_score=95,
                color="#10b981",
                risk_factors=RiskFactors(traffic=0.18, weather=0.15, incident=0.0, road=0.25, overall_risk=0.22),
                overall_score=0.20,
                predicted_delay_minutes=1.5,
                delay_prediction_source="ml",
                explanation_points=[
                    "✓ Sole viable highway corridor connecting origin and destination",
                    "✓ Zero alternative routes physically exist in vector road network",
                    "✓ Real-time telemetry confirmed open with smooth flow",
                ],
                tradeoff_summary="Only viable road network corridor found. Evaluated honestly with zero hallucinated alternatives.",
                coordinates=coords_a,
                is_passable=True,
            )
            resp = AnalyzeResponse(
                recommended_route="route-a",
                routes=[route_a],
                confidence=0.95,
                confidence_label="HIGH",
                confidence_percent=95,
                explanation=[
                    "Route A recommended (Single Viable Route):",
                    "• Sole physical corridor available in vector graph",
                    "• ⚠️ Only one viable route found. No alternative route is currently available.",
                    "• Zero hallucinated routes created",
                ],
                alternatives_available=False,
                origin_coords=origin_coords,
                destination_coords=dest_coords,
                incidents=[],
                optimization_profile=profile_dto,
                pipeline_timings_ms={"total_analyze_ms": 2.1, "sensor_ingestion_ms": 1.0},
            )
            return resp, "SCENARIO 7 — Only One Route Available Activated (DEMO DATA)"


# Singleton instance
demo_service = DemoService()
