"""
Traffic Agent

Detects traffic anomalies by comparing observed vs expected speed:
  speed_ratio = observed_speed / expected_speed

Classification:
  ratio >= 0.7   -> Normal flow, low traffic risk (0.10 - 0.25)
  0.4 <= ratio < 0.7 -> Moderate anomaly, moderate risk (0.25 - 0.55)
  ratio < 0.4    -> Severe anomaly, high risk (0.55 - 0.90)

CRITICAL: When a severe anomaly is detected, cause is ALWAYS flagged as "UNKNOWN"
unless an independent incident feed confirms a specific event. Traffic Agent
never invents or guesses causes.
"""

from dataclasses import dataclass
from typing import List, Optional
from backend.services.traffic_service import traffic_service, TrafficTelemetryData

# ==============================================================================
# Configurable Speed Ratio Threshold Constants
# ==============================================================================

SPEED_RATIO_NORMAL_THRESHOLD = 0.70
SPEED_RATIO_MODERATE_THRESHOLD = 0.40

# Risk Score Ranges
TRAFFIC_RISK_NORMAL_MIN = 0.10
TRAFFIC_RISK_NORMAL_MAX = 0.25
TRAFFIC_RISK_MODERATE_MIN = 0.25
TRAFFIC_RISK_MODERATE_MAX = 0.55
TRAFFIC_RISK_SEVERE_MIN = 0.55
TRAFFIC_RISK_SEVERE_MAX = 0.90


@dataclass
class TrafficEvaluationResult:
    """Traffic anomaly evaluation result for a candidate route corridor."""
    data_available: bool
    risk_score: Optional[float]
    risk_level: str  # "LOW", "MODERATE", "HIGH", "UNKNOWN"
    speed_ratio: Optional[float]
    observed_speed_kmh: Optional[float]
    expected_speed_kmh: Optional[float]
    has_anomaly: bool
    anomaly_severity: str  # "NONE", "MODERATE", "SEVERE"
    cause: str  # Strictly "UNKNOWN" when severe anomaly is detected without external confirmation
    explanation: str


class TrafficAgent:
    """
    Traffic agent evaluating congestion anomalies and speed ratios along routes.
    Maintains strict cause-agnostic honesty guard for telemetry.
    """

    def __init__(self):
        self.traffic_service = traffic_service

    def evaluate_route_traffic(
        self,
        coordinates: List[List[float]],
        road_name: str,
        current_hour: Optional[int] = None,
    ) -> TrafficEvaluationResult:
        """
        Evaluates traffic speed along a route corridor and assigns anomaly status and risk.
        """
        telemetry = self.traffic_service.get_route_traffic(
            coordinates=coordinates,
            road_name=road_name,
            current_hour=current_hour,
        )
        return self._classify_traffic_risk(telemetry)

    def _classify_traffic_risk(
        self, telemetry: Optional[TrafficTelemetryData]
    ) -> TrafficEvaluationResult:
        """
        Classifies traffic risk and anomalies based on telemetry observations.
        """
        # Failure guard: If traffic data source is unavailable, flag data_available: False
        if telemetry is None or not telemetry.data_available:
            return TrafficEvaluationResult(
                data_available=False,
                risk_score=None,
                risk_level="UNKNOWN",
                speed_ratio=None,
                observed_speed_kmh=None,
                expected_speed_kmh=None,
                has_anomaly=False,
                anomaly_severity="NONE",
                cause="UNKNOWN",
                explanation="⚠️ Traffic telemetry unavailable — risk assessment based on baseline cached models",
            )

        ratio = telemetry.congestion_ratio
        observed = telemetry.observed_speed_kmh
        expected = telemetry.expected_speed_kmh

        # Tier 3: Severe Traffic Anomaly (ratio < 0.40)
        if ratio < SPEED_RATIO_MODERATE_THRESHOLD:
            # Scaled score in [0.55, 0.90]
            deficit = (SPEED_RATIO_MODERATE_THRESHOLD - ratio) / SPEED_RATIO_MODERATE_THRESHOLD
            score = round(min(TRAFFIC_RISK_SEVERE_MAX, TRAFFIC_RISK_SEVERE_MIN + deficit * 0.35), 2)

            return TrafficEvaluationResult(
                data_available=True,
                risk_score=score,
                risk_level="HIGH",
                speed_ratio=ratio,
                observed_speed_kmh=observed,
                expected_speed_kmh=expected,
                has_anomaly=True,
                anomaly_severity="SEVERE",
                cause="UNKNOWN",  # STRICT RULE: Must be "UNKNOWN" without independent confirmation
                explanation=(
                    f"⚠️ Severe traffic anomaly: Observed speed {observed:.1f} km/h vs "
                    f"expected {expected:.1f} km/h (Speed Ratio {ratio:.2f}, Cause: UNKNOWN)"
                ),
            )

        # Tier 2: Moderate Traffic Anomaly (0.40 <= ratio < 0.70)
        elif ratio < SPEED_RATIO_NORMAL_THRESHOLD:
            deficit = (SPEED_RATIO_NORMAL_THRESHOLD - ratio) / (
                SPEED_RATIO_NORMAL_THRESHOLD - SPEED_RATIO_MODERATE_THRESHOLD
            )
            score = round(
                min(TRAFFIC_RISK_MODERATE_MAX, TRAFFIC_RISK_MODERATE_MIN + deficit * 0.30), 2
            )

            return TrafficEvaluationResult(
                data_available=True,
                risk_score=score,
                risk_level="MODERATE",
                speed_ratio=ratio,
                observed_speed_kmh=observed,
                expected_speed_kmh=expected,
                has_anomaly=True,
                anomaly_severity="MODERATE",
                cause="UNKNOWN",
                explanation=(
                    f"⚠️ Moderate traffic slowdown: Flow at {observed:.1f} km/h "
                    f"(Expected {expected:.1f} km/h, Speed Ratio {ratio:.2f})"
                ),
            )

        # Tier 1: Normal Free Flow (ratio >= 0.70)
        else:
            flow_efficiency = min(1.0, ratio / 1.0)
            score = round(
                max(
                    TRAFFIC_RISK_NORMAL_MIN,
                    TRAFFIC_RISK_NORMAL_MAX - (flow_efficiency - 0.70) * 0.20,
                ),
                2,
            )

            return TrafficEvaluationResult(
                data_available=True,
                risk_score=score,
                risk_level="LOW",
                speed_ratio=ratio,
                observed_speed_kmh=observed,
                expected_speed_kmh=expected,
                has_anomaly=False,
                anomaly_severity="NONE",
                cause="NONE",
                explanation=(
                    f"✓ Normal traffic flow: Observed {observed:.1f} km/h "
                    f"(Expected {expected:.1f} km/h, Speed Ratio {ratio:.2f})"
                ),
            )


# Singleton instance
traffic_agent = TrafficAgent()
