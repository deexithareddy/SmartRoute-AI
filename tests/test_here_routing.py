"""
tests/test_here_routing.py

Integration tests for HERE Routing API v8 and the provider fallback chain.

Test categories:
  1. Traffic status classification unit tests
  2. Provider configuration tests (raises cleanly when keys absent)
  3. HERE provider mock tests (no real API call needed)
  4. Provider fallback chain tests (HERE -> Geoapify)
  5. Live HERE API tests (skipped if HERE_API_KEY not configured)

Run with:
  python -m unittest tests.test_here_routing -v
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import HERE_API_KEY, GEOAPIFY_API_KEY
from backend.services.routing_providers import (
    HereRoutingProvider,
    GeoapifyRoutingProvider,
    _classify_traffic_status,
)

# Test corridors
HYDERABAD_LAT, HYDERABAD_LNG = 17.3850, 78.4867
SECUNDERABAD_LAT, SECUNDERABAD_LNG = 17.4399, 78.4983
RGIA_LAT, RGIA_LNG = 17.2403, 78.4294
SECUNDERABAD_STATION_LAT, SECUNDERABAD_STATION_LNG = 17.4387, 78.5013


# ===========================================================================
# 1. Traffic classification unit tests
# ===========================================================================
class TestTrafficClassification(unittest.TestCase):
    def test_low_zero_delay(self):
        self.assertEqual(_classify_traffic_status(0.0), "Low")

    def test_low_small_delay(self):
        self.assertEqual(_classify_traffic_status(60.0), "Low")

    def test_low_negative_delay(self):
        self.assertEqual(_classify_traffic_status(-90.0), "Low")

    def test_moderate_boundary_lower(self):
        self.assertEqual(_classify_traffic_status(120.0), "Moderate")

    def test_moderate_mid(self):
        self.assertEqual(_classify_traffic_status(300.0), "Moderate")

    def test_moderate_boundary_upper(self):
        self.assertEqual(_classify_traffic_status(599.0), "Moderate")

    def test_heavy(self):
        self.assertEqual(_classify_traffic_status(600.0), "Heavy")

    def test_heavy_severe(self):
        self.assertEqual(_classify_traffic_status(1800.0), "Heavy")


# ===========================================================================
# 2. Provider configuration tests
# ===========================================================================
class TestProviderConfiguration(unittest.TestCase):
    def test_here_provider_raises_without_key(self):
        import requests
        provider = HereRoutingProvider(session=requests.Session(), timeout=5)
        with patch("backend.services.routing_providers.HERE_API_KEY", ""):
            with self.assertRaises(ValueError) as ctx:
                provider.fetch_routes(17.38, 78.48, 17.43, 78.49)
            self.assertIn("HERE_API_KEY", str(ctx.exception))

    def test_geoapify_provider_raises_without_key(self):
        import requests
        provider = GeoapifyRoutingProvider(session=requests.Session(), timeout=5)
        with patch("backend.services.routing_providers.GEOAPIFY_API_KEY", ""):
            with self.assertRaises(ValueError) as ctx:
                provider.fetch_routes(17.38, 78.48, 17.43, 78.49)
            self.assertIn("GEOAPIFY_API_KEY", str(ctx.exception))


# ===========================================================================
# 3. HERE provider mock tests
# ===========================================================================
class TestHereProviderMocked(unittest.TestCase):
    def _make_provider(self):
        import requests
        return HereRoutingProvider(session=requests.Session(), timeout=5)

    def _mock_response(self, duration=900, typical_duration=1050, length=7800):
        return {
            "routes": [{
                "sections": [{
                    "summary": {
                        "duration": duration,
                        "length": length,
                        "typicalDuration": typical_duration,
                    },
                    "polyline": "",  # empty -> fallback to straight-line
                }]
            }]
        }

    def test_parses_response_correctly(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_response(duration=900, typical_duration=1200, length=7800)
        with patch("backend.services.routing_providers.HERE_API_KEY", "test-key"):
            with patch.object(provider.session, "get", return_value=mock_resp):
                routes = provider.fetch_routes(HYDERABAD_LAT, HYDERABAD_LNG, SECUNDERABAD_LAT, SECUNDERABAD_LNG)
        self.assertEqual(len(routes), 1)
        r = routes[0]
        self.assertEqual(r["data_source"], "here_live")
        self.assertEqual(r["provider"], "HERE")
        self.assertAlmostEqual(r["distance"], 7800.0)
        self.assertAlmostEqual(r["duration"], 900.0)
        # delay = 1200 - 900 = 300s = 5 min -> Moderate
        self.assertEqual(r["traffic_status"], "Moderate")
        self.assertAlmostEqual(r["traffic_delay_minutes"], 5.0)

    def test_raises_on_401(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch("backend.services.routing_providers.HERE_API_KEY", "bad-key"):
            with patch.object(provider.session, "get", return_value=mock_resp):
                with self.assertRaises(PermissionError):
                    provider.fetch_routes(HYDERABAD_LAT, HYDERABAD_LNG, SECUNDERABAD_LAT, SECUNDERABAD_LNG)

    def test_raises_on_503(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch("backend.services.routing_providers.HERE_API_KEY", "test-key"):
            with patch.object(provider.session, "get", return_value=mock_resp):
                with self.assertRaises(ConnectionError):
                    provider.fetch_routes(HYDERABAD_LAT, HYDERABAD_LNG, SECUNDERABAD_LAT, SECUNDERABAD_LNG)

    def test_traffic_low(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_response(duration=900, typical_duration=960)
        with patch("backend.services.routing_providers.HERE_API_KEY", "test-key"):
            with patch.object(provider.session, "get", return_value=mock_resp):
                routes = provider.fetch_routes(HYDERABAD_LAT, HYDERABAD_LNG, SECUNDERABAD_LAT, SECUNDERABAD_LNG)
        self.assertEqual(routes[0]["traffic_status"], "Low")

    def test_traffic_heavy(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_response(duration=900, typical_duration=1620)  # 720s delay
        with patch("backend.services.routing_providers.HERE_API_KEY", "test-key"):
            with patch.object(provider.session, "get", return_value=mock_resp):
                routes = provider.fetch_routes(HYDERABAD_LAT, HYDERABAD_LNG, SECUNDERABAD_LAT, SECUNDERABAD_LNG)
        self.assertEqual(routes[0]["traffic_status"], "Heavy")

    def test_key_not_in_log_url(self):
        """API key must not appear in any telemetry endpoint_url string."""
        from backend.services import telemetry_logger as tl_module
        logged_urls = []
        original_log = tl_module.telemetry_logger.log

        def capturing_log(*args, **kwargs):
            url = kwargs.get("endpoint_url", "")
            logged_urls.append(url)
            return original_log(*args, **kwargs)

        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_response()

        with patch("backend.services.routing_providers.HERE_API_KEY", "super-secret-key-abc123"):
            with patch.object(tl_module.telemetry_logger, "log", side_effect=capturing_log):
                with patch.object(provider.session, "get", return_value=mock_resp):
                    try:
                        provider.fetch_routes(HYDERABAD_LAT, HYDERABAD_LNG, SECUNDERABAD_LAT, SECUNDERABAD_LNG)
                    except Exception:
                        pass

        for url in logged_urls:
            self.assertNotIn("super-secret-key-abc123", url, f"API key found in telemetry URL: {url}")


# ===========================================================================
# 4. Fallback chain tests
# ===========================================================================
class TestProviderFallbackChain(unittest.TestCase):
    def setUp(self):
        from backend.services.routing_service import routing_service
        routing_service._routes_cache.clear()
        self.svc = routing_service

    def test_here_connectionerror_falls_through_to_geoapify(self):
        geo_routes = [
            {"distance": 7500.0, "duration": 960.0,
             "lat_lng_coordinates": [[HYDERABAD_LAT, HYDERABAD_LNG], [SECUNDERABAD_LAT, SECUNDERABAD_LNG]],
             "road_name": "Fallback Road", "provider": "GEOAPIFY", "data_source": "geoapify",
             "traffic_status": None, "traffic_delay_minutes": None, "legs": [], "waypoints": []}
        ]
        with patch("backend.services.routing_service.HERE_API_KEY", "test-key"):
            with patch.object(self.svc._here_provider, "fetch_routes", side_effect=ConnectionError("HERE down")):
                with patch.object(self.svc._geoapify_provider, "fetch_routes", return_value=geo_routes):
                    routes = self.svc.fetch_routes(HYDERABAD_LAT, HYDERABAD_LNG, SECUNDERABAD_LAT, SECUNDERABAD_LNG)
        self.assertGreater(len(routes), 0)
        self.assertEqual(routes[0]["data_source"], "geoapify")

    def test_here_permissionerror_does_not_fall_through(self):
        with patch("backend.services.routing_service.HERE_API_KEY", "bad-key"):
            with patch.object(self.svc._here_provider, "fetch_routes", side_effect=PermissionError("401")):
                with self.assertRaises(PermissionError):
                    self.svc.fetch_routes(HYDERABAD_LAT, HYDERABAD_LNG, SECUNDERABAD_LAT, SECUNDERABAD_LNG)

    def test_geoapify_routes_have_no_traffic_fields(self):
        geo_routes = [
            {"distance": 7500.0, "duration": 960.0,
             "lat_lng_coordinates": [[HYDERABAD_LAT, HYDERABAD_LNG], [SECUNDERABAD_LAT, SECUNDERABAD_LNG]],
             "road_name": "Test Road", "provider": "GEOAPIFY", "data_source": "geoapify",
             "traffic_status": None, "traffic_delay_minutes": None, "legs": [], "waypoints": []}
        ]
        with patch("backend.services.routing_service.HERE_API_KEY", ""):
            with patch.object(self.svc._geoapify_provider, "fetch_routes", return_value=geo_routes):
                routes = self.svc.fetch_routes(HYDERABAD_LAT, HYDERABAD_LNG, SECUNDERABAD_LAT, SECUNDERABAD_LNG)
        self.assertIsNone(routes[0]["traffic_status"])
        self.assertIsNone(routes[0]["traffic_delay_minutes"])


# ===========================================================================
# 5. Live HERE API tests (skipped if no key)
# ===========================================================================
@unittest.skipUnless(HERE_API_KEY, "HERE_API_KEY not configured — skipping live HERE API tests")
class TestHereProviderLive(unittest.TestCase):
    def setUp(self):
        import requests
        self.provider = HereRoutingProvider(session=requests.Session(), timeout=15)

    def test_hyderabad_to_secunderabad(self):
        routes = self.provider.fetch_routes(
            HYDERABAD_LAT, HYDERABAD_LNG,
            SECUNDERABAD_LAT, SECUNDERABAD_LNG,
            mode="drive", alternatives=True,
        )
        self.assertGreater(len(routes), 0)
        r = routes[0]
        self.assertEqual(r["data_source"], "here_live")
        self.assertIn(r["traffic_status"], ["Low", "Moderate", "Heavy"])
        self.assertIsNotNone(r["traffic_delay_minutes"])
        self.assertGreater(r["distance"], 1000)
        self.assertGreater(r["duration"], 60)
        self.assertGreater(len(r["lat_lng_coordinates"]), 2)
        print(f"\n[LIVE HERE] Hyd->Sec: {len(routes)} routes | {round(r['distance']/1000,1)} km | {round(r['duration']/60,1)} min | traffic={r['traffic_status']}")

    def test_rgia_to_secunderabad_station(self):
        routes = self.provider.fetch_routes(
            RGIA_LAT, RGIA_LNG,
            SECUNDERABAD_STATION_LAT, SECUNDERABAD_STATION_LNG,
            mode="drive", alternatives=True,
        )
        self.assertGreater(len(routes), 0)
        r = routes[0]
        self.assertEqual(r["data_source"], "here_live")
        self.assertIn(r["traffic_status"], ["Low", "Moderate", "Heavy"])
        self.assertGreater(r["distance"], 5000)
        print(f"\n[LIVE HERE] RGIA->Sec Stn: {len(routes)} routes | {round(r['distance']/1000,1)} km | traffic={r['traffic_status']}")

    def test_coordinates_in_hyderabad_region(self):
        routes = self.provider.fetch_routes(
            HYDERABAD_LAT, HYDERABAD_LNG,
            SECUNDERABAD_LAT, SECUNDERABAD_LNG,
        )
        for route in routes:
            for lat, lng in route["lat_lng_coordinates"]:
                self.assertGreater(lat, 16.0)
                self.assertLess(lat, 18.5)
                self.assertGreater(lng, 77.0)
                self.assertLess(lng, 80.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)