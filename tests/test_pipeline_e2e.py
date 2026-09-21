"""
SmartRoute AI - Comprehensive E2E Pipeline & Fault Tolerance Test Suite

Tests all 20 critical scenarios across the entire /api/analyze and /api/simulate pipeline:
  route_agent -> [traffic_agent, weather_agent, news_agent] -> risk_engine -> predictor -> optimizer_agent -> explainability
"""

import os
import sys
import unittest
from unittest.mock import patch

# Ensure repository root is on Python sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

from backend.main import app, run_orchestrated_pipeline
from backend.services.traffic_service import traffic_service
from backend.services.weather_service import weather_service
from backend.services.news_service import news_service
from backend.services.routing_service import routing_service
from backend.agents.traffic_agent import traffic_agent
from backend.agents.weather_agent import weather_agent
from backend.agents.news_agent import news_agent
from backend.agents.optimizer_agent import optimizer_agent
from backend.agents.simulation_agent import simulation_agent
from backend.ml.predictor import delay_predictor, DelayFeatureInput
from backend.models.schemas import RouteResult, RiskFactors, SimulateRequest

client = TestClient(app)


class TestSmartRoutePipeline(unittest.TestCase):
    """Full test suite covering all 20 required pipeline scenarios."""

    def setUp(self):
        """Ensure all telemetry feeds are online before each test."""
        traffic_service.set_online_status(True)
        weather_service.set_online_status(True)
        news_service.set_online_status(True)
        routing_service.set_online_status(True)

    def tearDown(self):
        """Restore all telemetry feeds to online after each test."""
        traffic_service.set_online_status(True)
        weather_service.set_online_status(True)
        news_service.set_online_status(True)
        routing_service.set_online_status(True)

    # --------------------------------------------------------------------------
    # Case 1: Normal request
    # --------------------------------------------------------------------------
    def test_case_01_normal_request(self):
        response = client.post(
            "/api/analyze",
            json={
                "source": "Hyderabad, India",
                "destination": "Secunderabad, India",
                "vehicle_type": "Ambulance",
                "priority": "Critical",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("recommended_route", data)
        self.assertGreaterEqual(len(data["routes"]), 1)
        self.assertGreaterEqual(len(data["explanation"]), 1)
        self.assertEqual(data["confidence_label"], "HIGH")
        self.assertEqual(data["confidence_percent"], 95)

    # --------------------------------------------------------------------------
    # Case 2: Ambulance request (High Wt speed weight prioritization)
    # --------------------------------------------------------------------------
    def test_case_02_ambulance_request(self):
        # 1. Direct optimizer test
        r_fast = RouteResult(
            id="route-fast",
            code="Route A",
            name="Fast Arterial",
            eta_minutes=15,
            distance_km=10.0,
            risk_percent=35,
            status="MODERATE",
            is_recommended=False,
            reliability_score=0.75,
            confidence_score=95,
            color="#ef4444",
            risk_factors=RiskFactors(traffic=0.35, weather=0.10, incident=0.10, road=0.30, overall_risk=0.35),
            coordinates=[[12.9716, 77.5946], [12.9352, 77.6245]],
        )
        r_slow = RouteResult(
            id="route-slow",
            code="Route B",
            name="Safe Ring",
            eta_minutes=25,
            distance_km=15.0,
            risk_percent=15,
            status="LOW",
            is_recommended=False,
            reliability_score=0.90,
            confidence_score=95,
            color="#10b981",
            risk_factors=RiskFactors(traffic=0.10, weather=0.10, incident=0.00, road=0.20, overall_risk=0.15),
            coordinates=[[12.9716, 77.5946], [12.9352, 77.6245]],
        )
        ranked, rec = optimizer_agent.optimize_routes([r_fast, r_slow], vehicle_type="Ambulance", priority="Critical")
        self.assertEqual(rec.id, "route-fast")

        # 2. HTTP Endpoint test
        response = client.post(
            "/api/analyze",
            json={
                "source": "Hyderabad, India",
                "destination": "Secunderabad, India",
                "vehicle_type": "Ambulance",
                "priority": "Critical",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("recommended_route", data)

    # --------------------------------------------------------------------------
    # Case 3: Medical Supply Truck request (High Wl reliability weight)
    # --------------------------------------------------------------------------
    def test_case_03_medical_supply_truck_request(self):
        # 1. Direct optimizer test: Supply truck prefers high reliability over raw speed
        r_fast_risky = RouteResult(
            id="route-fast-risky",
            code="Route A",
            name="Congested Arterial",
            eta_minutes=16,
            distance_km=10.0,
            risk_percent=55,
            status="HIGH",
            is_recommended=False,
            reliability_score=0.45,
            confidence_score=95,
            color="#ef4444",
            risk_factors=RiskFactors(traffic=0.65, weather=0.10, incident=0.75, road=0.30, overall_risk=0.55),
            coordinates=[[17.3850, 78.4867], [17.4399, 78.4983]],
        )
        r_reliable = RouteResult(
            id="route-reliable",
            code="Route B",
            name="Reliable Bypass",
            eta_minutes=19,
            distance_km=14.0,
            risk_percent=15,
            status="LOW",
            is_recommended=False,
            reliability_score=0.90,
            confidence_score=95,
            color="#10b981",
            risk_factors=RiskFactors(traffic=0.15, weather=0.10, incident=0.00, road=0.20, overall_risk=0.15),
            coordinates=[[17.3850, 78.4867], [17.4399, 78.4983]],
        )
        ranked, rec = optimizer_agent.optimize_routes(
            [r_fast_risky, r_reliable], vehicle_type="Medical Supply Truck", priority="Standard"
        )
        self.assertEqual(rec.id, "route-reliable")

        # 2. HTTP Endpoint test
        response = client.post(
            "/api/analyze",
            json={
                "source": "Hyderabad, India",
                "destination": "Secunderabad, India",
                "vehicle_type": "Medical Supply Truck",
                "priority": "Standard",
            },
        )
        self.assertEqual(response.status_code, 200)

    # --------------------------------------------------------------------------
    # Case 4: Disaster Relief request (High Wr safety + accessibility weight)
    # --------------------------------------------------------------------------
    def test_case_04_disaster_relief_request(self):
        response = client.post(
            "/api/analyze",
            json={
                "source": "Hyderabad, India",
                "destination": "Secunderabad, India",
                "vehicle_type": "Disaster Relief Vehicle",
                "priority": "Standard",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("recommended_route", data)
        recommended = next(r for r in data["routes"] if r["id"] == data["recommended_route"])
        self.assertGreaterEqual(recommended["reliability_score"], 0.50)

    # --------------------------------------------------------------------------
    # Case 5: High traffic anomaly (Speed ratio < 0.40 with cause: UNKNOWN)
    # --------------------------------------------------------------------------
    def test_case_05_high_traffic_anomaly(self):
        # 1. Direct severe anomaly classification test
        from backend.services.traffic_service import TrafficTelemetryData
        mock_tel = TrafficTelemetryData(
            data_available=True,
            observed_speed_kmh=12.0,
            expected_speed_kmh=48.0,
            congestion_ratio=0.25,
            road_class="Arterial",
            sample_coordinates_count=10,
            timestamp="2026-08-30T14:45:00Z",
        )
        severe_eval = traffic_agent._classify_traffic_risk(mock_tel)
        self.assertTrue(severe_eval.has_anomaly)
        self.assertEqual(severe_eval.risk_level, "HIGH")
        self.assertEqual(severe_eval.cause, "UNKNOWN")
        self.assertIn("Cause: UNKNOWN", severe_eval.explanation)

        # 2. General route evaluation test
        res = traffic_agent.evaluate_route_traffic(
            coordinates=[[17.3850, 78.4867], [17.4399, 78.4983]],
            road_name="NH765 Corridor, Hyderabad",
            current_hour=18,
        )
        self.assertIn(res.risk_level, ["MODERATE", "HIGH", "LOW"])

    # --------------------------------------------------------------------------
    # Case 6: Heavy rainfall (Precipitation > 25mm -> severe weather risk)
    # --------------------------------------------------------------------------
    def test_case_06_heavy_rainfall(self):
        risk_score, risk_level, explanation = weather_agent._classify_weather_risk(
            max_rain_mm=35.0,
            max_wind_kmh=45.0,
            min_visibility_m=1200.0,
            has_storm=True,
            condition_desc="Thunderstorm with Heavy Rain",
        )
        self.assertIn(risk_level.upper(), ["HIGH", "SEVERE"])
        self.assertGreaterEqual(risk_score, 0.50)

    # --------------------------------------------------------------------------
    # Case 7: Reported incident (Active CAD incident matched along polyline)
    # --------------------------------------------------------------------------
    def test_case_07_reported_incident(self):
        # Whitefield Road polyline intersects INC-BLR-001 at (12.9930, 77.7058)
        route_coords = [[12.9925, 77.7050], [12.9935, 77.7065]]
        inc_eval = news_agent.evaluate_route_incidents(route_coords)
        self.assertTrue(inc_eval.has_incidents)
        self.assertGreater(inc_eval.incident_risk_score, 0.0)
        self.assertIn("collision", inc_eval.matched_incidents[0].headline.lower())

    # --------------------------------------------------------------------------
    # Case 8: No incident (Clean bypass corridor)
    # --------------------------------------------------------------------------
    def test_case_08_no_incident(self):
        remote_coords = [[13.1500, 77.8500], [13.1600, 77.8600]]
        inc_eval = news_agent.evaluate_route_incidents(remote_coords)
        self.assertFalse(inc_eval.has_incidents)
        self.assertEqual(inc_eval.incident_risk_score, 0.0)

    # --------------------------------------------------------------------------
    # Case 9: Traffic source unavailable (Graceful degradation to 75% confidence)
    # --------------------------------------------------------------------------
    def test_case_09_traffic_source_unavailable(self):
        traffic_service.set_online_status(False)
        response = client.post(
            "/api/analyze",
            json={
                "source": "Hyderabad, India",
                "destination": "Secunderabad, India",
                "vehicle_type": "Medical Supply Truck",
                "priority": "Standard",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["confidence_label"], "MODERATE")
        self.assertEqual(data["confidence_percent"], 75)
        self.assertTrue(any("Traffic telemetry unavailable" in exp for exp in data["explanation"]))

    # --------------------------------------------------------------------------
    # Case 10: Weather source unavailable
    # --------------------------------------------------------------------------
    def test_case_10_weather_source_unavailable(self):
        weather_service.set_online_status(False)
        response = client.post(
            "/api/analyze",
            json={
                "source": "Hyderabad, India",
                "destination": "Secunderabad, India",
                "vehicle_type": "Medical Supply Truck",
                "priority": "Standard",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["confidence_label"], "MODERATE")
        self.assertEqual(data["confidence_percent"], 75)

    # --------------------------------------------------------------------------
    # Case 11: News source unavailable
    # --------------------------------------------------------------------------
    def test_case_11_news_source_unavailable(self):
        news_service.set_online_status(False)
        response = client.post(
            "/api/analyze",
            json={
                "source": "Hyderabad, India",
                "destination": "Secunderabad, India",
                "vehicle_type": "Medical Supply Truck",
                "priority": "Standard",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["confidence_label"], "MODERATE")
        self.assertEqual(data["confidence_percent"], 75)

    # --------------------------------------------------------------------------
    # Case 12: Single candidate route or alternative corridors
    # --------------------------------------------------------------------------
    def test_case_12_only_one_route_available(self):
        response = client.post(
            "/api/analyze",
            json={
                "source": "17.3850, 78.4867",
                "destination": "17.3855, 78.4870",
                "vehicle_type": "Ambulance",
                "priority": "Critical",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("recommended_route", data)
        self.assertGreaterEqual(len(data["routes"]), 1)

    # --------------------------------------------------------------------------
    # Case 13: No valid route / Geocoding failure (Strict no-fabrication contract)
    # --------------------------------------------------------------------------
    def test_case_13_no_valid_route(self):
        response = client.post(
            "/api/analyze",
            json={
                "source": "NonExistentPlaceXYZ987654321",
                "destination": "AnotherUnknownPlace123456789",
                "vehicle_type": "Ambulance",
                "priority": "Critical",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unable to geocode", response.json()["detail"])

    # --------------------------------------------------------------------------
    # Case 14: ML prediction available (Healthy telemetry -> source: ml)
    # --------------------------------------------------------------------------
    def test_case_14_ml_prediction_available(self):
        features = DelayFeatureInput(
            observed_speed_kmh=22.0,
            expected_speed_kmh=48.0,
            baseline_duration_minutes=20.0,
            rainfall_mm=10.0,
            traffic_available=True,
            weather_available=True,
        )
        pred = delay_predictor.predict_delay(features)
        self.assertEqual(pred.source, "ml")
        self.assertGreater(pred.predicted_delay_minutes, 0.0)
        self.assertGreaterEqual(pred.confidence, 0.90)

    # --------------------------------------------------------------------------
    # Case 15: ML fallback (Missing inputs -> source: rule_based)
    # --------------------------------------------------------------------------
    def test_case_15_ml_fallback(self):
        features = DelayFeatureInput(
            observed_speed_kmh=None,
            expected_speed_kmh=48.0,
            baseline_duration_minutes=20.0,
            traffic_available=False,
            weather_available=True,
        )
        pred = delay_predictor.predict_delay(features)
        self.assertEqual(pred.source, "rule_based")
        self.assertIn("Rule-based", pred.explanation)

    # --------------------------------------------------------------------------
    # Case 16: Scenario simulation (Zero baseline mutation + side-by-side output)
    # --------------------------------------------------------------------------
    def test_case_16_scenario_simulation(self):
        r1 = RouteResult(
            id="r-a",
            code="Route A",
            name="Corridor 1",
            eta_minutes=15,
            distance_km=10.0,
            risk_percent=20,
            status="LOW",
            is_recommended=True,
            reliability_score=0.85,
            confidence_score=95,
            color="#ef4444",
            risk_factors=RiskFactors(traffic=0.20, weather=0.10, incident=0.0, road=0.20, overall_risk=0.15),
            coordinates=[[12.9716, 77.5946], [12.9352, 77.6245]],
        )
        r2 = RouteResult(
            id="r-b",
            code="Route B",
            name="Corridor 2",
            eta_minutes=20,
            distance_km=14.0,
            risk_percent=15,
            status="LOW",
            is_recommended=False,
            reliability_score=0.90,
            confidence_score=95,
            color="#10b981",
            risk_factors=RiskFactors(traffic=0.15, weather=0.10, incident=0.0, road=0.20, overall_risk=0.15),
            coordinates=[[12.9716, 77.5946], [12.9352, 77.6245]],
        )
        sim_res = simulation_agent.run_simulation(
            baseline_routes=[r1, r2],
            request=SimulateRequest(
                rainfall=45.0,
                traffic_multiplier=1.8,
                road_closure=False,
                duration_hours=1.0,
            ),
        )
        self.assertEqual(len(sim_res.comparison), 2)
        # Verify baseline route object was NOT mutated
        self.assertEqual(r1.risk_percent, 20)

    # --------------------------------------------------------------------------
    # Case 17: Road closure simulation (Corridor marked is_passable: False)
    # --------------------------------------------------------------------------
    def test_case_17_road_closure_simulation(self):
        r1 = RouteResult(
            id="route-a",
            code="Route A",
            name="Primary Arterial",
            eta_minutes=15,
            distance_km=10.0,
            risk_percent=20,
            status="LOW",
            is_recommended=True,
            reliability_score=0.85,
            confidence_score=95,
            color="#ef4444",
            risk_factors=RiskFactors(traffic=0.20, weather=0.10, incident=0.0, road=0.20, overall_risk=0.15),
            coordinates=[[12.9716, 77.5946], [12.9352, 77.6245]],
        )
        sim_res = simulation_agent.run_simulation(
            baseline_routes=[r1],
            request=SimulateRequest(
                rainfall=20.0,
                traffic_multiplier=1.5,
                road_closure=True,
                duration_hours=1.0,
            ),
        )
        comp_a = sim_res.comparison[0]
        self.assertFalse(comp_a.is_passable)
        self.assertEqual(comp_a.simulated_risk_percent, 100)
        self.assertEqual(comp_a.simulated_status, "CRITICAL")

    # --------------------------------------------------------------------------
    # Case 18: Invalid user input (Empty strings / Whitespace / Special Characters)
    # --------------------------------------------------------------------------
    def test_case_18_invalid_user_input(self):
        response = client.post(
            "/api/analyze",
            json={
                "source": "   ",
                "destination": "!@#$%^&*()",
                "vehicle_type": "Ambulance",
                "priority": "Critical",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    # --------------------------------------------------------------------------
    # Case 19: External API timeout (Isolated error boundaries)
    # --------------------------------------------------------------------------
    def test_case_19_external_api_timeout(self):
        with patch.object(weather_service.session, "get", side_effect=TimeoutError("Request timed out")):
            response = client.post(
                "/api/analyze",
                json={
                    "source": "Hyderabad, India",
                    "destination": "Secunderabad, India",
                    "vehicle_type": "Ambulance",
                    "priority": "Critical",
                },
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertGreaterEqual(len(data["routes"]), 1)

    # --------------------------------------------------------------------------
    # Case 20: Multiple external APIs failing simultaneously (Max degradation)
    # --------------------------------------------------------------------------
    def test_case_20_multiple_external_apis_failing_simultaneously(self):
        traffic_service.set_online_status(False)
        weather_service.set_online_status(False)
        news_service.set_online_status(False)

        response = client.post(
            "/api/analyze",
            json={
                "source": "Hyderabad, India",
                "destination": "Secunderabad, India",
                "vehicle_type": "Ambulance",
                "priority": "Critical",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["confidence_percent"], 25)
        self.assertEqual(data["confidence_label"], "VERY LOW")
        self.assertIn("recommended_route", data)

    # --------------------------------------------------------------------------
    # Case 21: Unsupported region rejection (Prototype Hyderabad constraint)
    # --------------------------------------------------------------------------
    def test_case_21_unsupported_region_rejection(self):
        response = client.post(
            "/api/analyze",
            json={
                "source": "Indiranagar, Bengaluru",
                "destination": "Whitefield, Bengaluru",
                "vehicle_type": "Ambulance",
                "priority": "Critical",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("This prototype currently supports emergency routing within Hyderabad.", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
