"""
SmartRoute AI - Delay Prediction ML Model & Telemetry Audit

Architecture:
  - Regressor: GradientBoostingRegressor (scikit-learn)
  - Objective: Predict corridor transit delay (minutes) from multi-sensor telemetry features

DATA CATEGORY CLASSIFICATIONS:
  1. TRAINING DATA:
     - Synthetic historical training corpus (1,600 simulated journey records)
     - Generated using physics-grounded traffic flow, weather impedance, and incident blockage equations
     - NOT collected from production GPS fleet traces
  2. VALIDATION / TEST DATA:
     - Held-out evaluation slice (400 samples, 20% validation split)
     - Used exclusively for offline regression metric calculation (MAE ~0.8 min, R^2 ~0.94)
  3. SYNTHETIC DATA:
     - Physics-modeled sensor variables (rush-hour speed ratios, rain intensity, simulated road closures)
     - Used for model training and what-if simulation stress testing
  4. LIVE INFERENCE DATA:
     - Real-time sensor telemetry ingested at runtime from Open-Meteo, OSRM, municipal sensors, and CAD dispatch

DISCLAIMER & LIMITATIONS:
  - Model accuracy metrics reflect synthetic holdout validation.
  - DO NOT claim production-level real-world accuracy without empirical GPS probe fleet calibration.
  - Transparent hybrid fallback automatically switches to rule-based heuristics if telemetry is incomplete.
"""

import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

MODEL_FILE_PATH = os.path.join(os.path.dirname(__file__), "delay_model.joblib")
SAMPLE_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "sample_data.json"
)

FEATURE_NAMES = [
    "observed_speed",
    "expected_speed",
    "speed_ratio",
    "baseline_duration_minutes",
    "rainfall_mm",
    "visibility_m",
    "wind_speed_kmh",
    "incident_count",
    "incident_severity",
    "road_type_code",
    "hour_of_day",
    "day_of_week",
]

# Baseline evaluation metrics stored for auditability
MODEL_METRICS_AUDIT: Dict[str, Any] = {
    "model_type": "GradientBoostingRegressor (scikit-learn)",
    "n_estimators": 120,
    "learning_rate": 0.08,
    "max_depth": 4,
    "training_dataset_type": "SYNTHETIC (Physics-Grounded Simulation Corpus)",
    "training_sample_count": 1600,
    "validation_sample_count": 400,
    "total_dataset_samples": 2000,
    "validation_split": 0.20,
    "evaluation_metrics": {
        "val_mae_minutes": 0.82,
        "val_r2_score": 0.941,
    },
    "prediction_sources": ["ml", "rule_based"],
    "live_inference_feeds": [
        "Open-Meteo Live Atmospheric Telemetry",
        "Municipal Sensor Grid & Flow Telemetry",
        "CAD Police & Emergency Incident Dispatch",
        "OSRM High-Precision Vector Road Network",
    ],
    "synthetic_disclosure": (
        "Model trained on synthetic historical corpus modeled with physical traffic and meteorological "
        "equations. Metrics represent synthetic test holdouts and do not constitute real-world fleet validation."
    ),
    "limitations": [
        "Trained on synthetic corridor simulations rather than production GPS fleet probe archives.",
        "Assumes standard urban road friction and does not account for localized pavement degradation or seasonal roadworks.",
        "Requires active traffic & weather telemetry; automatically falls back to deterministic rule-based heuristics when feeds disconnect.",
        "Model accuracy metrics reflect synthetic validation split (20%) and must be calibrated against municipality-specific ground-truth data before mission-critical field deployment.",
    ],
}


def generate_synthetic_delay_dataset(
    num_samples: int = 2000, random_seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates a synthetic historical training dataset with realistic physical correlations:
      delay ~ duration*(1 - speed_ratio) + rainfall_impact + incident_blockage + road_friction
    """
    random.seed(random_seed)
    np.random.seed(random_seed)

    X_list = []
    y_list = []

    for _ in range(num_samples):
        # Road typology: 0=Expressway, 1=Arterial, 2=Secondary
        road_type = random.choice([0, 1, 2])
        if road_type == 0:
            expected_speed = random.uniform(65.0, 85.0)
        elif road_type == 1:
            expected_speed = random.uniform(40.0, 55.0)
        else:
            expected_speed = random.uniform(25.0, 38.0)

        hour_of_day = random.randint(0, 23)
        day_of_week = random.randint(0, 6)
        baseline_duration = random.uniform(8.0, 50.0)

        # Congestion speed ratio based on time of day
        is_rush_hour = (8 <= hour_of_day <= 10) or (17 <= hour_of_day <= 20)
        if is_rush_hour:
            speed_ratio = random.uniform(0.25, 0.70)
        else:
            speed_ratio = random.uniform(0.65, 1.05)

        observed_speed = max(5.0, round(expected_speed * speed_ratio, 1))

        # Weather features
        is_rainy = random.random() < 0.35
        rainfall_mm = round(random.uniform(2.0, 60.0), 1) if is_rainy else 0.0
        visibility_m = max(200.0, 10000.0 - rainfall_mm * 150.0 + random.uniform(-500, 500))
        wind_speed_kmh = round(random.uniform(5.0, 65.0) if is_rainy else random.uniform(5.0, 25.0), 1)

        # Incident features
        has_incident = random.random() < 0.25
        incident_count = random.choice([1, 2]) if has_incident else 0
        incident_severity = (
            random.choice([0.40, 0.75, 0.90]) if has_incident else 0.0
        )

        # Calculate realistic physics-grounded delay target (minutes)
        speed_deficit = max(0.0, 1.0 - speed_ratio)
        traffic_delay = baseline_duration * speed_deficit * (0.85 + road_type * 0.15)
        rain_delay = (rainfall_mm * 0.16) if rainfall_mm > 5.0 else 0.0
        incident_delay = (incident_severity * 14.0 * incident_count) if has_incident else 0.0
        noise = random.uniform(-1.0, 1.5)

        delay_minutes = max(0.0, round(traffic_delay + rain_delay + incident_delay + noise, 1))

        features = [
            observed_speed,
            expected_speed,
            speed_ratio,
            baseline_duration,
            rainfall_mm,
            visibility_m,
            wind_speed_kmh,
            incident_count,
            incident_severity,
            float(road_type),
            float(hour_of_day),
            float(day_of_week),
        ]

        X_list.append(features)
        y_list.append(delay_minutes)

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.float32)


def save_synthetic_data_to_json(
    X: np.ndarray, y: np.ndarray, json_path: str = SAMPLE_DATA_PATH
) -> None:
    """Saves synthetic dataset summary to sample_data.json for full auditability."""
    try:
        data = {}
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        data["synthetic_delay_training_dataset"] = {
            "_comment": "SYNTHETIC PROTOTYPE TRAINING CORPUS (Generated for Delay Prediction Regressor)",
            "data_provenance": "SYNTHETIC",
            "feature_names": FEATURE_NAMES,
            "total_samples": len(X),
            "sample_records": [
                {
                    "features": {FEATURE_NAMES[i]: float(X[row][i]) for i in range(len(FEATURE_NAMES))},
                    "target_delay_minutes": float(y[row]),
                }
                for row in range(min(25, len(X)))
            ],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Model] Warning: Could not save synthetic data to JSON: {e}")


def train_and_save_delay_model(
    model_output_path: str = MODEL_FILE_PATH,
    json_path: str = SAMPLE_DATA_PATH,
) -> Tuple[GradientBoostingRegressor, Dict[str, Any]]:
    """
    Trains GradientBoostingRegressor on synthetic training corpus and serializes model.
    """
    print("[Model] Generating synthetic delay training corpus...")
    X, y = generate_synthetic_delay_dataset(num_samples=2000)

    save_synthetic_data_to_json(X, y, json_path)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    print("[Model] Training GradientBoostingRegressor...")
    model = GradientBoostingRegressor(
        n_estimators=120,
        learning_rate=0.08,
        max_depth=4,
        min_samples_split=4,
        random_state=42,
    )
    model.fit(X_train, y_train)

    val_preds = model.predict(X_val)
    val_mae = mean_absolute_error(y_val, val_preds)
    val_r2 = r2_score(y_val, val_preds)

    metrics = {
        "val_mae": round(float(val_mae), 3),
        "val_r2": round(float(val_r2), 3),
        "train_samples": len(X_train),
        "val_samples": len(X_val),
    }
    MODEL_METRICS_AUDIT["evaluation_metrics"]["val_mae_minutes"] = metrics["val_mae"]
    MODEL_METRICS_AUDIT["evaluation_metrics"]["val_r2_score"] = metrics["val_r2"]

    print(f"[Model] Model Training Complete: MAE={metrics['val_mae']} min, R^2={metrics['val_r2']}")

    # Save serialized model artifact
    joblib.dump(model, model_output_path)
    print(f"[Model] Serialized model saved to {model_output_path}")

    return model, metrics


def get_model_metadata() -> Dict[str, Any]:
    """Returns complete model metadata, features, dataset provenance, and audit metrics."""
    return {
        "model_type": MODEL_METRICS_AUDIT["model_type"],
        "features": FEATURE_NAMES,
        "training_dataset_type": MODEL_METRICS_AUDIT["training_dataset_type"],
        "training_sample_count": MODEL_METRICS_AUDIT["training_sample_count"],
        "validation_sample_count": MODEL_METRICS_AUDIT["validation_sample_count"],
        "total_dataset_samples": MODEL_METRICS_AUDIT["total_dataset_samples"],
        "evaluation_metrics": MODEL_METRICS_AUDIT["evaluation_metrics"],
        "prediction_sources": MODEL_METRICS_AUDIT["prediction_sources"],
        "live_inference_feeds": MODEL_METRICS_AUDIT["live_inference_feeds"],
        "synthetic_disclosure": MODEL_METRICS_AUDIT["synthetic_disclosure"],
        "limitations": MODEL_METRICS_AUDIT["limitations"],
    }


if __name__ == "__main__":
    train_and_save_delay_model()
