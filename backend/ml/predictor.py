"""
Delay Predictor

Exposes `predict_delay(features)` with a robust hybrid fallback architecture:
  - If multi-sensor features are complete and healthy -> ML model inference (source: "ml")
  - If key telemetry inputs are missing/offline -> Rule-based heuristic fallback (source: "rule_based")
"""

import datetime
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import joblib
import numpy as np

from backend.ml.model import FEATURE_NAMES, MODEL_FILE_PATH, train_and_save_delay_model


@dataclass
class DelayPredictionResult:
    """Predicted transit delay outcome with hybrid source attribution."""
    predicted_delay_minutes: float
    source: str  # "ml" | "rule_based"
    confidence: float
    explanation: str


@dataclass
class DelayFeatureInput:
    """Input telemetry features for delay estimation."""
    observed_speed_kmh: Optional[float]
    expected_speed_kmh: Optional[float]
    baseline_duration_minutes: float
    rainfall_mm: Optional[float] = 0.0
    visibility_m: Optional[float] = 10000.0
    wind_speed_kmh: Optional[float] = 10.0
    incident_count: int = 0
    incident_severity: float = 0.0
    road_name: str = ""
    traffic_available: bool = True
    weather_available: bool = True


class DelayPredictor:
    """
    ML delay predictor with automated fallback to rule-based heuristics.
    """

    def __init__(self, model_path: str = MODEL_FILE_PATH):
        self.model_path = model_path
        self.model = None
        self._load_or_train_model()

    def _load_or_train_model(self) -> None:
        """Loads serialized model artifact or trains a fresh one if absent."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                print(f"[Predictor] Model artifact not found at {self.model_path}. Training new model...")
                self.model, _ = train_and_save_delay_model(self.model_path)
        except Exception as e:
            print(f"[Predictor] Error loading model artifact: {e}")
            self.model = None

    def _get_road_type_code(self, road_name: str) -> float:
        """Maps road name to road type code (0=Expressway, 1=Arterial, 2=Secondary)."""
        name_lower = (road_name or "").lower()
        if any(kw in name_lower for kw in ["expressway", "flyover", "elevated", "bypass", "motorway"]):
            return 0.0
        elif any(kw in name_lower for kw in ["arterial", "main road", "avenue", "ring road", "mg road"]):
            return 1.0
        return 2.0

    def _rule_based_fallback(
        self, features: DelayFeatureInput, reason: str
    ) -> DelayPredictionResult:
        """
        Transparent rule-based delay heuristic executed when ML model or features are unavailable.
        """
        eta = max(1.0, float(features.baseline_duration_minutes))

        # Speed ratio calculation
        if (
            features.observed_speed_kmh is not None
            and features.expected_speed_kmh is not None
            and features.expected_speed_kmh > 0
        ):
            speed_ratio = features.observed_speed_kmh / features.expected_speed_kmh
        else:
            speed_ratio = 0.75  # Neutral assumption

        # Congestion delay
        congestion_deficit = max(0.0, 1.0 - speed_ratio)
        traffic_delay = eta * congestion_deficit * 0.70

        # Weather delay
        rain = features.rainfall_mm or 0.0
        rain_delay = (rain * 0.15) if rain > 5.0 else 0.0

        # Incident delay
        incident_delay = (features.incident_severity * 12.0 * max(1, features.incident_count)) if features.incident_count > 0 else 0.0

        total_delay = round(max(0.0, traffic_delay + rain_delay + incident_delay), 1)

        return DelayPredictionResult(
            predicted_delay_minutes=total_delay,
            source="rule_based",
            confidence=0.68,
            explanation=f"⚙️ Rule-based delay estimate (+{total_delay}m): {reason}",
        )

    def predict_delay(self, features: DelayFeatureInput) -> DelayPredictionResult:
        """
        Executes ML delay prediction if features are complete and model is loaded;
        otherwise executes graceful rule-based fallback.
        """
        # Guard 1: Telemetry availability check
        if not features.traffic_available or features.observed_speed_kmh is None:
            return self._rule_based_fallback(
                features, reason="Traffic telemetry offline (Using flow heuristics)"
            )

        if not features.weather_available or features.rainfall_mm is None:
            return self._rule_based_fallback(
                features, reason="Weather telemetry offline (Using baseline precipitation)"
            )

        # Guard 2: Model artifact check
        if self.model is None:
            return self._rule_based_fallback(
                features, reason="ML model artifact offline"
            )

        try:
            now = datetime.datetime.now()
            hour_of_day = float(now.hour)
            day_of_week = float(now.weekday())

            observed_speed = float(features.observed_speed_kmh)
            expected_speed = float(features.expected_speed_kmh or 45.0)
            speed_ratio = observed_speed / expected_speed if expected_speed > 0 else 1.0
            baseline_duration = float(features.baseline_duration_minutes)
            rainfall_mm = float(features.rainfall_mm or 0.0)
            visibility_m = float(features.visibility_m or 10000.0)
            wind_speed_kmh = float(features.wind_speed_kmh or 10.0)
            incident_count = float(features.incident_count)
            incident_severity = float(features.incident_severity)
            road_type_code = self._get_road_type_code(features.road_name)

            feature_vector = np.array(
                [
                    [
                        observed_speed,
                        expected_speed,
                        speed_ratio,
                        baseline_duration,
                        rainfall_mm,
                        visibility_m,
                        wind_speed_kmh,
                        incident_count,
                        incident_severity,
                        road_type_code,
                        hour_of_day,
                        day_of_week,
                    ]
                ],
                dtype=np.float32,
            )

            pred = self.model.predict(feature_vector)[0]
            delay_minutes = round(max(0.0, float(pred)), 1)

            return DelayPredictionResult(
                predicted_delay_minutes=delay_minutes,
                source="ml",
                confidence=0.92,
                explanation=f"🤖 ML-predicted delay: +{delay_minutes} min (Gradient Boosting model)",
            )

        except Exception as e:
            print(f"[Predictor] ML inference error: {e}. Falling back to rule-based estimate.")
            return self._rule_based_fallback(
                features, reason="Inference exception caught"
            )


# Singleton instance
delay_predictor = DelayPredictor()
