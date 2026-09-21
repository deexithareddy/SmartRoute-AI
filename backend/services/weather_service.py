"""
Weather Service

Integrates with the Open-Meteo public API (no API key required) to fetch
real-time precipitation, wind speed, visibility, and atmospheric conditions.
Includes structured telemetry logging and transparent provenance labeling.
"""

import time
from typing import Any, Dict, Optional, Tuple
import requests

from backend.services.telemetry_logger import telemetry_logger

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "SmartRouteAI/1.0 (Emergency Weather Risk Evaluation)"


class WeatherService:
    """Service client for fetching live weather data from Open-Meteo."""

    def __init__(self, timeout_seconds: int = 6):
        self.timeout = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        # Simple coordinate-based cache: (lat_rounded, lng_rounded) -> (timestamp, data)
        self._cache: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}
        self.cache_ttl_seconds = 300  # 5 minutes
        self._is_online = True

    def set_online_status(self, is_online: bool) -> None:
        """Allows toggling provider availability for testing and fault-injection."""
        self._is_online = is_online

    def is_healthy(self) -> bool:
        """Returns True if the Open-Meteo weather service is enabled/online."""
        return self._is_online

    def get_weather_for_coordinate(
        self, lat: float, lng: float
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches current weather observations for a specific latitude and longitude.
        Returns a normalized dictionary of metrics or None if request fails.
        """
        start_time = time.time()
        if not self._is_online:
            latency = (time.time() - start_time) * 1000.0
            telemetry_logger.log(
                service_name="Open-Meteo Atmospheric Telemetry",
                endpoint_url=OPEN_METEO_URL,
                request_status="FAULT_INJECTED",
                response_status=None,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message="Weather feed forced UNAVAILABLE via fault-injection",
            )
            return None

        # Round to 2 decimal places (~1.1 km resolution) for caching efficiency
        cache_key = (round(lat, 2), round(lng, 2))
        now = time.time()

        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if now - cached_time < self.cache_ttl_seconds:
                latency = (time.time() - start_time) * 1000.0
                telemetry_logger.log(
                    service_name="Open-Meteo Atmospheric Telemetry",
                    endpoint_url=OPEN_METEO_URL,
                    request_status="CACHED_HIT",
                    response_status=200,
                    latency_ms=latency,
                    provenance="CACHED",
                    success=True,
                    details={
                        "lat": lat,
                        "lng": lng,
                        "cache_age_sec": round(now - cached_time, 1),
                        "rain_mm": cached_data.get("rain_mm"),
                    },
                )
                return cached_data

        params = {
            "latitude": lat,
            "longitude": lng,
            "current": "precipitation,rain,wind_speed_10m,weather_code,visibility",
            "timezone": "auto",
        }

        try:
            response = self.session.get(
                OPEN_METEO_URL, params=params, timeout=self.timeout
            )
            latency = (time.time() - start_time) * 1000.0

            if response.status_code == 200:
                payload = response.json()
                current = payload.get("current", {})

                precipitation_mm = float(current.get("precipitation", 0.0) or 0.0)
                rain_mm = float(current.get("rain", 0.0) or 0.0)
                wind_speed_kmh = float(current.get("wind_speed_10m", 0.0) or 0.0)
                weather_code = int(current.get("weather_code", 0) or 0)
                raw_visibility = current.get("visibility")
                visibility_meters = (
                    float(raw_visibility) if raw_visibility is not None else 10000.0
                )

                is_storm = weather_code in {95, 96, 99}
                condition_desc = self._get_weather_code_description(weather_code)

                result = {
                    "precipitation_mm": precipitation_mm,
                    "rain_mm": rain_mm,
                    "wind_speed_kmh": wind_speed_kmh,
                    "visibility_meters": visibility_meters,
                    "weather_code": weather_code,
                    "is_storm": is_storm,
                    "weather_description": condition_desc,
                    "lat": lat,
                    "lng": lng,
                }

                self._cache[cache_key] = (now, result)
                telemetry_logger.log(
                    service_name="Open-Meteo Atmospheric Telemetry",
                    endpoint_url=OPEN_METEO_URL,
                    request_status="SENT",
                    response_status=200,
                    latency_ms=latency,
                    provenance="LIVE",
                    success=True,
                    details={
                        "lat": lat,
                        "lng": lng,
                        "rain_mm": rain_mm,
                        "wind_kmh": wind_speed_kmh,
                        "desc": condition_desc,
                    },
                )
                return result
            else:
                telemetry_logger.log(
                    service_name="Open-Meteo Atmospheric Telemetry",
                    endpoint_url=OPEN_METEO_URL,
                    request_status="SENT",
                    response_status=response.status_code,
                    latency_ms=latency,
                    provenance="UNAVAILABLE",
                    success=False,
                    error_message=f"Open-Meteo returned HTTP {response.status_code}",
                )
                return None
        except Exception as e:
            latency = (time.time() - start_time) * 1000.0
            telemetry_logger.log(
                service_name="Open-Meteo Atmospheric Telemetry",
                endpoint_url=OPEN_METEO_URL,
                request_status="SENT",
                response_status=None,
                latency_ms=latency,
                provenance="UNAVAILABLE",
                success=False,
                error_message=str(e),
            )
            return None

    def _get_weather_code_description(self, code: int) -> str:
        """Translates WMO weather code into human-readable description."""
        code_map = {
            0: "Clear skies",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy conditions",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snowfall",
            73: "Moderate snowfall",
            75: "Heavy snowfall",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return code_map.get(code, f"Atmospheric condition (Code {code})")


# Singleton instance
weather_service = WeatherService()
