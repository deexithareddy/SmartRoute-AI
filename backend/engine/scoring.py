"""
Scoring Engine

Implements the Route Optimizer's multi-criteria scoring function:
  Route Score = Wt * ETA_score + Wr * Risk_score + Wd * Delay_score + Wl * Reliability_score

All four factors are normalized to comparable 0.0–1.0 penalty scales (lower is better).

Explicit Mission Profiles:
  1. AMBULANCE:
     - Speed: Very High (Wt = 0.45, Critical: 0.55)
     - Safety: Very High (Wr = 0.35)
     - Reliability: High (Wl = 0.15)
     - Delay: Low (Wd = 0.05)

  2. MEDICAL SUPPLY:
     - Speed: Medium (Wt = 0.20)
     - Safety: High (Wr = 0.30)
     - Reliability: Very High (Wl = 0.35)
     - Delay: Medium (Wd = 0.15)

  3. DISASTER RELIEF:
     - Speed: Medium (Wt = 0.15)
     - Safety: Very High (Wr = 0.35)
     - Reliability: Very High (Wl = 0.30)
     - Accessibility: Very High (Wacc = 0.20)

Weights are fully configurable and dynamically adjustable.
"""

from typing import Dict, List, Optional, Any
from copy import deepcopy

# ==============================================================================
# Default Mission Profile Weight Configurations
# ==============================================================================

DEFAULT_MISSION_PROFILES: Dict[str, Dict[str, Any]] = {
    "Ambulance": {
        "name": "Ambulance (EMS / Critical Care)",
        "speed_rating": "Very High",
        "safety_rating": "Very High",
        "reliability_rating": "High",
        "accessibility_rating": "Standard",
        "weights": {
            "wt": 0.45,  # Speed / Nominal ETA
            "wr": 0.35,  # Safety / Risk Score
            "wd": 0.05,  # Predicted Delay
            "wl": 0.15,  # Travel Time Reliability
        },
        "description": "Speed: Very High | Safety: Very High | Reliability: High",
    },
    "Medical Supply Truck": {
        "name": "Medical Supply Truck (Logistics & Delivery)",
        "speed_rating": "Medium",
        "safety_rating": "High",
        "reliability_rating": "Very High",
        "accessibility_rating": "High",
        "weights": {
            "wt": 0.20,  # Speed / Nominal ETA
            "wr": 0.30,  # Safety / Risk Score
            "wd": 0.15,  # Predicted Delay
            "wl": 0.35,  # Travel Time Reliability
        },
        "description": "Speed: Medium | Safety: High | Reliability: Very High",
    },
    "Disaster Relief Vehicle": {
        "name": "Disaster Relief (Heavy Response / Evacuation)",
        "speed_rating": "Medium",
        "safety_rating": "Very High",
        "reliability_rating": "Very High",
        "accessibility_rating": "Very High",
        "weights": {
            "wt": 0.15,  # Speed / Nominal ETA
            "wr": 0.35,  # Safety / Risk Score
            "wd": 0.20,  # Road Accessibility / Disruption Avoidance
            "wl": 0.30,  # Travel Time Reliability
        },
        "description": "Speed: Medium | Safety: Very High | Reliability: Very High | Accessibility: Very High",
    },
}


class ScoringEngine:
    """
    Computes normalized multi-criteria route scores for vehicle mission profiles.
    Allows runtime configuration of weight profiles.
    """

    def __init__(self):
        self.active_profiles: Dict[str, Dict[str, Any]] = deepcopy(DEFAULT_MISSION_PROFILES)

    def reset_profiles(self) -> None:
        """Resets all profile weights back to system defaults."""
        self.active_profiles = deepcopy(DEFAULT_MISSION_PROFILES)

    def configure_profile(self, vehicle_type: str, weights: Dict[str, float]) -> Dict[str, Any]:
        """
        Updates the weights for a specific vehicle mission profile.
        Normalizes weights to sum to 1.0.
        """
        key = self._resolve_profile_key(vehicle_type)
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("Weights must sum to a positive value.")

        normalized_w = {k: round(v / total, 4) for k, v in weights.items()}
        self.active_profiles[key]["weights"] = normalized_w
        return self.active_profiles[key]

    def _resolve_profile_key(self, vehicle_type: str) -> str:
        """Maps arbitrary input strings to canonical profile keys."""
        v_type = (vehicle_type or "").lower().strip()
        if "supply" in v_type or "truck" in v_type or "logistics" in v_type:
            return "Medical Supply Truck"
        elif "disaster" in v_type or "relief" in v_type or "evacuation" in v_type:
            return "Disaster Relief Vehicle"
        return "Ambulance"

    def get_profile_details(self, vehicle_type: str, priority: str = "Critical") -> Dict[str, Any]:
        """
        Returns full metadata and configuration for the active optimization profile.
        """
        key = self._resolve_profile_key(vehicle_type)
        prof = self.active_profiles.get(key, self.active_profiles["Ambulance"])

        clean_vehicle = "Ambulance" if key == "Ambulance" else "Medical Supply" if "Supply" in key else "Disaster Relief"
        clean_priority = priority.capitalize() if priority else "Critical"

        return {
            "key": key,
            "vehicle_type": clean_vehicle,
            "priority": clean_priority,
            "profile_label": f"Optimization profile: {clean_vehicle} / {clean_priority}",
            "speed": prof["speed_rating"],
            "safety": prof["safety_rating"],
            "reliability": prof["reliability_rating"],
            "accessibility": prof["accessibility_rating"],
            "weights": prof["weights"],
            "description": prof["description"],
        }

    def get_weights_for_vehicle(self, vehicle_type: str) -> Dict[str, float]:
        """
        Returns active weights dictionary for the requested vehicle type.
        """
        key = self._resolve_profile_key(vehicle_type)
        return self.active_profiles[key]["weights"]

    def normalize_eta(self, eta_minutes: float, all_etas: List[float]) -> float:
        """
        Normalizes ETA across candidate routes to a 0.0–1.0 penalty score.
        Proportionally penalizes travel time differences relative to transit scale.
        """
        if not all_etas or len(all_etas) <= 1:
            return min(1.0, max(0.0, eta_minutes / 60.0))

        min_eta = min(all_etas)
        max_eta = max(all_etas)

        if max_eta - min_eta < 1e-4:
            return 0.50

        # Blended scaling: evaluates both relative corridor gap and absolute transit time ratio
        relative_gap = (eta_minutes - min_eta) / max(10.0, max_eta - min_eta)
        absolute_ratio = (eta_minutes - min_eta) / max(1.0, min_eta)
        score = 0.60 * relative_gap + 0.40 * absolute_ratio

        return round(min(1.0, max(0.0, score)), 4)

    def normalize_delay(self, delay_minutes: float, eta_minutes: float) -> float:
        """
        Normalizes predicted delay to a 0.0–1.0 penalty score relative to transit duration.
        """
        if eta_minutes <= 0:
            return 0.0
        # A delay equal to 50% or more of nominal ETA represents full penalty (1.0)
        delay_ratio = max(0.0, delay_minutes) / (0.50 * eta_minutes)
        return round(min(1.0, delay_ratio), 4)

    def compute_route_score(
        self,
        eta_score: float,
        risk_score: float,
        delay_score: float,
        reliability: float,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Calculates:
          Route Score = Wt*ETA_score + Wr*Risk_score + Wd*Delay_score + Wl*(1.0 - Reliability)
        Lower score = Better route.
        """
        w = weights or self.get_weights_for_vehicle("Ambulance")

        wt = w.get("wt", 0.45)
        wr = w.get("wr", 0.35)
        wd = w.get("wd", 0.05)
        wl = w.get("wl", 0.15)

        # Reliability penalty: 1.0 - reliability (e.g. 95% reliability -> 0.05 penalty)
        reliability_penalty = max(0.0, min(1.0, 1.0 - float(reliability)))

        score = (
            wt * max(0.0, min(1.0, float(eta_score)))
            + wr * max(0.0, min(1.0, float(risk_score)))
            + wd * max(0.0, min(1.0, float(delay_score)))
            + wl * reliability_penalty
        )

        return round(max(0.0, min(1.0, score)), 4)


# Singleton instance
scoring_engine = ScoringEngine()
