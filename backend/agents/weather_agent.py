"""
Weather Agent

Classifies weather risk per route segment (rainfall, wind, visibility, storms)
into Low/Moderate/High/Severe, using configurable thresholds.

If telemetry fails, explicitly flags data_available: false rather than
substituting a false 'Low Risk' default.
"""

import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from backend.services.weather_service import weather_service

# ==============================================================================
# Configurable Weather Risk Thresholds (Named Constants)
# ==============================================================================

# Rainfall / Precipitation thresholds (mm/h)
RAIN_MODERATE_THRESHOLD_MM = 2.5
RAIN_HEAVY_THRESHOLD_MM = 10.0
RAIN_SEVERE_THRESHOLD_MM = 30.0

# Wind Speed thresholds (km/h)
WIND_MODERATE_THRESHOLD_KMH = 30.0
WIND_HEAVY_THRESHOLD_KMH = 50.0
WIND_SEVERE_THRESHOLD_KMH = 75.0

# Visibility thresholds (meters)
VISIBILITY_MODERATE_THRESHOLD_M = 3000.0
VISIBILITY_POOR_THRESHOLD_M = 1000.0
VISIBILITY_CRITICAL_THRESHOLD_M = 400.0

# WMO Storm / Thunderstorm Codes
STORM_WMO_CODES = {95, 96, 99}

# Risk Score Range Constants
RISK_SCORE_NORMAL_MIN = 0.10
RISK_SCORE_NORMAL_MAX = 0.25
RISK_SCORE_MODERATE_MIN = 0.26
RISK_SCORE_MODERATE_MAX = 0.50
RISK_SCORE_HIGH_MIN = 0.51
RISK_SCORE_HIGH_MAX = 0.75
RISK_SCORE_SEVERE_MIN = 0.76
RISK_SCORE_SEVERE_MAX = 1.00


@dataclass
class WeatherEvaluationResult:
    """Evaluation result containing calculated risk score and grounded telemetry details."""
    data_available: bool
    risk_score: Optional[float]
    risk_level: str  # "Low", "Moderate", "High", "Severe", "UNKNOWN"
    max_rain_mm: float = 0.0
    max_wind_kmh: float = 0.0
    min_visibility_m: float = 10000.0
    has_storm: bool = False
    dominant_condition: str = "Clear"
    explanation: str = ""
    sample_points_count: int = 0
    raw_samples: List[Dict[str, Any]] = field(default_factory=list)


class WeatherAgent:
    """
    Evaluates weather risk along route segments by sampling route polyline
    coordinates and classifying against configurable risk thresholds.
    """

    def __init__(self):
        self.weather_service = weather_service

    def sample_route_coordinates(
        self, coordinates: List[List[float]], max_samples: int = 5
    ) -> List[Tuple[float, float]]:
        """
        Extracts representative coordinates along the polyline (e.g. start, 25%, 50%, 75%, end).
        """
        if not coordinates:
            return []
        if len(coordinates) <= max_samples:
            return [(c[0], c[1]) for c in coordinates]

        step = (len(coordinates) - 1) / (max_samples - 1)
        sampled: List[Tuple[float, float]] = []
        for i in range(max_samples):
            idx = min(int(round(i * step)), len(coordinates) - 1)
            c = coordinates[idx]
            sampled.append((c[0], c[1]))
        return sampled

    def evaluate_route_weather(
        self, coordinates: List[List[float]]
    ) -> WeatherEvaluationResult:
        """
        Samples weather along the route polyline and computes composite weather risk.
        Returns WeatherEvaluationResult with data_available flag.
        """
        sampled_coords = self.sample_route_coordinates(coordinates, max_samples=4)
        if not sampled_coords:
            return WeatherEvaluationResult(
                data_available=False,
                risk_score=None,
                risk_level="UNKNOWN",
                explanation="⚠️ Weather evaluation skipped: No route coordinates provided",
            )

        # Deduplicate rounded coordinates to avoid redundant network calls
        unique_coords = list({(round(lat, 2), round(lng, 2)): (lat, lng) for lat, lng in sampled_coords}.values())

        samples: List[Dict[str, Any]] = []
        if unique_coords:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(unique_coords))) as executor:
                future_to_coord = {
                    executor.submit(self.weather_service.get_weather_for_coordinate, lat, lng): (lat, lng)
                    for lat, lng in unique_coords
                }
                for future in concurrent.futures.as_completed(future_to_coord):
                    try:
                        obs = future.result()
                        if obs:
                            samples.append(obs)
                    except Exception:
                        pass

        # If Open-Meteo failed for all sampled points, strictly flag data_available: False
        if not samples:
            return WeatherEvaluationResult(
                data_available=False,
                risk_score=None,
                risk_level="UNKNOWN",
                explanation="⚠️ Real-time weather telemetry unavailable (Open-Meteo connection offline)",
                sample_points_count=0,
            )

        # Aggregate worst-case / peak conditions across corridor segments
        max_rain = max(s["precipitation_mm"] for s in samples)
        max_wind = max(s["wind_speed_kmh"] for s in samples)
        min_visibility = min(s["visibility_meters"] for s in samples)
        has_storm = any(s["is_storm"] for s in samples)
        dominant_condition = samples[0]["weather_description"]

        # Classify risk score based on configurable rules
        risk_score, risk_level, explanation = self._classify_weather_risk(
            max_rain_mm=max_rain,
            max_wind_kmh=max_wind,
            min_visibility_m=min_visibility,
            has_storm=has_storm,
            condition_desc=dominant_condition,
        )

        return WeatherEvaluationResult(
            data_available=True,
            risk_score=risk_score,
            risk_level=risk_level,
            max_rain_mm=max_rain,
            max_wind_kmh=max_wind,
            min_visibility_m=min_visibility,
            has_storm=has_storm,
            dominant_condition=dominant_condition,
            explanation=explanation,
            sample_points_count=len(samples),
            raw_samples=samples,
        )

    def _classify_weather_risk(
        self,
        max_rain_mm: float,
        max_wind_kmh: float,
        min_visibility_m: float,
        has_storm: bool,
        condition_desc: str,
    ) -> Tuple[float, str, str]:
        """
        Applies configurable thresholds to assign risk score (0.10 - 1.00) and explanation.
        """
        # Tier 4: Severe / Extreme Risk (0.75 - 1.00)
        if (
            has_storm
            or max_rain_mm >= RAIN_SEVERE_THRESHOLD_MM
            or max_wind_kmh >= WIND_SEVERE_THRESHOLD_KMH
            or min_visibility_m <= VISIBILITY_CRITICAL_THRESHOLD_M
        ):
            # Scale dynamically in range [0.76, 1.00]
            score = min(
                1.0,
                RISK_SCORE_SEVERE_MIN
                + 0.15 * (max_rain_mm / 50.0)
                + 0.10 * (max_wind_kmh / 100.0),
            )
            score = round(max(RISK_SCORE_SEVERE_MIN, min(1.0, score)), 2)
            hazards = []
            if has_storm:
                hazards.append("Thunderstorm alert")
            if max_rain_mm >= RAIN_SEVERE_THRESHOLD_MM:
                hazards.append(f"Torrential rain ({max_rain_mm:.1f}mm/h)")
            if max_wind_kmh >= WIND_SEVERE_THRESHOLD_KMH:
                hazards.append(f"Severe gale wind ({max_wind_kmh:.1f}km/h)")
            if min_visibility_m <= VISIBILITY_CRITICAL_THRESHOLD_M:
                hazards.append(f"Critical visibility ({min_visibility_m:.0f}m)")
            hazard_str = ", ".join(hazards)
            return (
                score,
                "Severe",
                f"⛔ Severe weather risk along corridor: {hazard_str}",
            )

        # Tier 3: High Risk (0.50 - 0.75)
        if (
            max_rain_mm >= RAIN_HEAVY_THRESHOLD_MM
            or max_wind_kmh >= WIND_HEAVY_THRESHOLD_KMH
            or min_visibility_m <= VISIBILITY_POOR_THRESHOLD_M
        ):
            score = min(
                RISK_SCORE_HIGH_MAX,
                RISK_SCORE_HIGH_MIN
                + 0.15 * ((max_rain_mm - RAIN_HEAVY_THRESHOLD_MM) / 20.0)
                + 0.10 * ((max_wind_kmh - WIND_HEAVY_THRESHOLD_KMH) / 25.0),
            )
            score = round(max(RISK_SCORE_HIGH_MIN, min(RISK_SCORE_HIGH_MAX, score)), 2)
            hazards = []
            if max_rain_mm >= RAIN_HEAVY_THRESHOLD_MM:
                hazards.append(f"Heavy rain ({max_rain_mm:.1f}mm/h)")
            if max_wind_kmh >= WIND_HEAVY_THRESHOLD_KMH:
                hazards.append(f"High wind gusts ({max_wind_kmh:.1f}km/h)")
            if min_visibility_m <= VISIBILITY_POOR_THRESHOLD_M:
                hazards.append(f"Poor visibility ({min_visibility_m:.0f}m)")
            hazard_str = ", ".join(hazards)
            return (
                score,
                "High",
                f"⚠️ High weather hazard: {hazard_str}",
            )

        # Tier 2: Moderate Risk (0.25 - 0.50)
        if (
            max_rain_mm >= RAIN_MODERATE_THRESHOLD_MM
            or max_wind_kmh >= WIND_MODERATE_THRESHOLD_KMH
            or min_visibility_m <= VISIBILITY_MODERATE_THRESHOLD_M
        ):
            score = min(
                RISK_SCORE_MODERATE_MAX,
                RISK_SCORE_MODERATE_MIN
                + 0.15 * ((max_rain_mm - RAIN_MODERATE_THRESHOLD_MM) / 7.5)
                + 0.10 * ((max_wind_kmh - WIND_MODERATE_THRESHOLD_KMH) / 20.0),
            )
            score = round(
                max(RISK_SCORE_MODERATE_MIN, min(RISK_SCORE_MODERATE_MAX, score)), 2
            )
            return (
                score,
                "Moderate",
                f"⚠️ Moderate weather impact: Rain {max_rain_mm:.1f}mm/h, Wind {max_wind_kmh:.1f}km/h",
            )

        # Tier 1: Normal Conditions / Low Risk (0.10 - 0.25)
        score = round(
            RISK_SCORE_NORMAL_MIN
            + 0.10 * (max_rain_mm / RAIN_MODERATE_THRESHOLD_MM)
            + 0.05 * (max_wind_kmh / WIND_MODERATE_THRESHOLD_KMH),
            2,
        )
        score = max(RISK_SCORE_NORMAL_MIN, min(RISK_SCORE_NORMAL_MAX, score))
        vis_km = f"{min_visibility_m/1000.0:.1f}km" if min_visibility_m < 10000 else ">10km"
        return (
            score,
            "Low",
            f"✓ Favorable weather ({condition_desc}, Rain: {max_rain_mm:.1f}mm, Wind: {max_wind_kmh:.1f}km/h, Vis: {vis_km})",
        )


# Singleton instance
weather_agent = WeatherAgent()
