"""
Risk Engine

Implements the transparent multi-factor weighted formula:
  Overall Risk = 0.35 * Traffic Risk
               + 0.25 * Weather Risk
               + 0.25 * Incident Risk
               + 0.15 * Road Risk

All factor inputs and the composite score are normalized 0.0 to 1.0.
Weights are configurable named constants.
"""

from typing import Dict, Optional, Tuple

# ==============================================================================
# Configurable Named Weight Constants
# ==============================================================================

WEIGHT_TRAFFIC = 0.35
WEIGHT_WEATHER = 0.25
WEIGHT_INCIDENT = 0.25
WEIGHT_ROAD = 0.15

# Total weight validation safeguard
TOTAL_WEIGHT = WEIGHT_TRAFFIC + WEIGHT_WEATHER + WEIGHT_INCIDENT + WEIGHT_ROAD
assert abs(TOTAL_WEIGHT - 1.0) < 1e-6, f"Risk weights must sum to 1.0, got {TOTAL_WEIGHT}"

# ==============================================================================
# Risk Bands Definition
# ==============================================================================

BAND_LOW_MAX = 0.25
BAND_MODERATE_MAX = 0.50
BAND_HIGH_MAX = 0.75
BAND_SEVERE_MAX = 1.00

# ==============================================================================
# Confidence Degradation Bands (Based on Active Telemetry Feeds)
# ==============================================================================
# 4/4 Live -> HIGH (95% certainty)
# 3/4 Live -> MODERATE (75% certainty)
# 2/4 Live -> LOW (50% certainty)
# <=1/4 Live -> VERY LOW (25% certainty)


class RiskEngine:
    """
    Core risk computation engine for calculating multi-factor composite risk,
    risk band labels, road risk heuristics, and confidence degradation.
    """

    def __init__(
        self,
        weight_traffic: float = WEIGHT_TRAFFIC,
        weight_weather: float = WEIGHT_WEATHER,
        weight_incident: float = WEIGHT_INCIDENT,
        weight_road: float = WEIGHT_ROAD,
    ):
        self.w_traffic = weight_traffic
        self.w_weather = weight_weather
        self.w_incident = weight_incident
        self.w_road = weight_road

    def estimate_road_risk(self, road_name: str) -> float:
        """
        Estimates road infrastructure risk based on road typology/class keywords.
        Returns a score in [0.0, 1.0] (lower is safer/better infrastructure).
        """
        if not road_name:
            return 0.30  # Neutral default

        name_lower = road_name.lower()

        # Grade-separated expressways / highways / bypasses have lowest infrastructure hazard
        if any(kw in name_lower for kw in ["expressway", "motorway", "flyover", "elevated", "bypass", "highway"]):
            return 0.15

        # Primary urban arterials / avenues / ring roads
        if any(kw in name_lower for kw in ["arterial", "avenue", "ring road", "main road", "boulevard"]):
            return 0.30

        # Narrower residential / cross streets / market roads have higher congestion & obstacle risk
        if any(kw in name_lower for kw in ["cross", "lane", "street", "residential", "market", "bazaar"]):
            return 0.45

        return 0.30  # Neutral fallback

    def compute_overall_risk(
        self,
        traffic_risk: float,
        weather_risk: float,
        incident_risk: float,
        road_risk: float,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Calculates Overall Risk = W_t*Traffic + W_w*Weather + W_i*Incident + W_r*Road
        Ensures all inputs and the output remain strictly normalized [0.0, 1.0].
        """
        # Clamp inputs between 0.0 and 1.0
        t = max(0.0, min(1.0, float(traffic_risk)))
        w = max(0.0, min(1.0, float(weather_risk)))
        i = max(0.0, min(1.0, float(incident_risk)))
        r = max(0.0, min(1.0, float(road_risk)))

        wt = weights.get("traffic", self.w_traffic) if weights else self.w_traffic
        ww = weights.get("weather", self.w_weather) if weights else self.w_weather
        wi = weights.get("incident", self.w_incident) if weights else self.w_incident
        wr = weights.get("road", self.w_road) if weights else self.w_road

        overall = (wt * t) + (ww * w) + (wi * i) + (wr * r)
        return round(max(0.0, min(1.0, overall)), 4)

    def map_risk_to_label(self, score: float) -> str:
        """
        Maps a 0.0–1.0 risk score to its corresponding risk band label:
          0.00–0.25  LOW
          0.25–0.50  MODERATE
          0.50–0.75  HIGH
          0.75–1.00  SEVERE
        """
        s = max(0.0, min(1.0, score))
        if s <= BAND_LOW_MAX:
            return "LOW"
        elif s <= BAND_MODERATE_MAX:
            return "MODERATE"
        elif s <= BAND_HIGH_MAX:
            return "HIGH"
        else:
            return "SEVERE"

    def calculate_confidence(
        self, feed_availability: Dict[str, bool]
    ) -> Tuple[str, int, float]:
        """
        Calculates system confidence based on upstream telemetry availability.
        Returns:
            - label: "HIGH" | "MODERATE" | "LOW" | "VERY LOW"
            - percent: int (e.g. 95, 75, 50, 25)
            - score: float (0.0 to 1.0)
        """
        if not feed_availability:
            return "LOW", 50, 0.50

        total_feeds = len(feed_availability)
        live_feeds = sum(1 for is_live in feed_availability.values() if is_live)
        ratio = live_feeds / total_feeds if total_feeds > 0 else 0.0

        if ratio >= 1.0:
            return "HIGH", 95, 0.95
        elif ratio >= 0.75:
            return "MODERATE", 75, 0.75
        elif ratio >= 0.50:
            return "LOW", 50, 0.50
        else:
            return "VERY LOW", 25, 0.25


# Singleton instance
risk_engine = RiskEngine()
