import os
import sys
import unittest
from unittest.mock import patch

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.config import GEOAPIFY_API_KEY
from backend.main import app
from backend.services.routing_service import routing_service
from backend.agents.route_agent import route_agent

client = TestClient(app)


class TestGeoapifyIntegration(unittest.TestCase):
    """
    Comprehensive test suite for Geoapify Routing & Geocoding API integration.
    """

    def setUp(self):
        routing_service.set_online_status(True)

    def test_01_api_key_loaded_and_not_empty(self):
        """Requirement 1, 3, 4: Key loaded from environment, not hardcoded, verified at runtime without printing."""
        self.assertTrue(bool(GEOAPIFY_API_KEY), "GEOAPIFY_API_KEY must be present in backend environment.")
        self.assertGreaterEqual(len(GEOAPIFY_API_KEY), 30, "GEOAPIFY_API_KEY must have valid token length.")

    def test_02_geoapify_geocoding_hyderabad_and_secunderabad(self):
        """Test Geoapify geocoding for Hyderabad and Secunderabad."""
        origin_lat, origin_lng, origin_name = routing_service.geocode("Hyderabad, India")
        dest_lat, dest_lng, dest_name = routing_service.geocode("Secunderabad, India")

        self.assertAlmostEqual(origin_lat, 17.36, delta=0.1)
        self.assertAlmostEqual(origin_lng, 78.47, delta=0.1)
        self.assertAlmostEqual(dest_lat, 17.43, delta=0.1)
        self.assertAlmostEqual(dest_lng, 78.50, delta=0.1)
        self.assertTrue(len(origin_name) > 0)
        self.assertTrue(len(dest_name) > 0)

    def test_03_geoapify_routing_hyderabad_to_secunderabad(self):
        """Requirement 5, 6, 7: Test Geoapify Routing API with Source: Hyderabad, Destination: Secunderabad, Mode: drive."""
        origin_lat, origin_lng, _ = routing_service.geocode("Hyderabad, India")
        dest_lat, dest_lng, _ = routing_service.geocode("Secunderabad, India")

        routes = routing_service.fetch_routes_geoapify(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            mode="drive",
            alternatives=True,
        )

        self.assertGreaterEqual(len(routes), 1, "At least 1 candidate route should be returned by Geoapify.")
        primary_route = routes[0]
        self.assertEqual(primary_route["provider"], "GEOAPIFY")
        self.assertGreater(primary_route["distance"], 5000.0)  # ~10-13 km
        self.assertGreater(primary_route["duration"], 300.0)   # ~10-20 min
        self.assertIn("geometry", primary_route)
        self.assertIn("lat_lng_coordinates", primary_route)
        self.assertGreater(len(primary_route["lat_lng_coordinates"]), 10, "Route must contain realistic polyline coordinates.")
        # Coordinates must be [lat, lng] format (Leaflet compatible)
        first_coord = primary_route["lat_lng_coordinates"][0]
        self.assertAlmostEqual(first_coord[0], origin_lat, delta=0.05)
        self.assertAlmostEqual(first_coord[1], origin_lng, delta=0.05)

    def test_04_route_agent_candidate_generation_separation(self):
        """Requirement 7, 10: Verify RouteAgent constructs clean RouteResult without computing risk."""
        routes, alternatives_avail, origin_coords, dest_coords = route_agent.get_candidate_routes(
            source="Hyderabad, India",
            destination="Secunderabad, India",
            mode="drive",
        )
        self.assertGreaterEqual(len(routes), 1)
        r0 = routes[0]
        self.assertEqual(r0.risk_percent, 0, "RouteAgent must keep risk_percent=0 prior to RiskEngine evaluation.")
        self.assertFalse(r0.is_recommended, "RouteAgent must not pick recommendation prior to OptimizerAgent.")
        self.assertGreater(len(r0.coordinates), 10)
        self.assertGreater(r0.distance_km, 5.0)

    def test_05_api_analyze_returns_real_route_and_geometry(self):
        """Requirement 8, 9: Make sure /api/analyze returns real route info and geometry for frontend."""
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
        self.assertEqual(data["confidence_label"], "HIGH")

        rec_route = next(r for r in data["routes"] if r["id"] == data["recommended_route"])
        self.assertTrue(rec_route["is_recommended"])
        self.assertGreater(len(rec_route["coordinates"]), 10)
        self.assertGreater(rec_route["distance_km"], 5.0)
        self.assertGreater(rec_route["eta_minutes"], 5)
        self.assertIn("Charminar", rec_route["name"] + " " + " ".join(rec_route["explanation_points"]))

    def test_06_error_handling_no_fabrication_on_failure(self):
        """Requirement 11: If routing provider fails, return clear backend error and do not fabricate fake data."""
        routing_service.set_online_status(False)
        response = client.post(
            "/api/analyze",
            json={
                "source": "Hyderabad, India",
                "destination": "Secunderabad, India",
                "vehicle_type": "Ambulance",
                "priority": "Critical",
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("unavailable", response.json()["detail"].lower())

    def test_07_health_and_docs_endpoints(self):
        """Requirement 12: Test /api/health, /health, and /docs endpoints."""
        resp_health1 = client.get("/api/health")
        self.assertEqual(resp_health1.status_code, 200)
        self.assertEqual(resp_health1.json(), {"status": "ok"})

        resp_health2 = client.get("/health")
        self.assertEqual(resp_health2.status_code, 200)
        self.assertEqual(resp_health2.json(), {"status": "ok"})

        resp_docs = client.get("/docs")
        self.assertEqual(resp_docs.status_code, 200)


if __name__ == "__main__":
    unittest.main()
