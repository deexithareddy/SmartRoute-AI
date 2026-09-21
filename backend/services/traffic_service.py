"""
Traffic Service

High-level traffic service managing the active TrafficProvider implementation
(SimulatedTrafficProvider vs RealTrafficProvider), demo scenario injections,
and telemetry provenance tracking.
"""

from typing import List, Literal, Optional
from backend.services.traffic_provider import (
    TrafficProvider,
    SimulatedTrafficProvider,
    RealTrafficProvider,
    TrafficTelemetryData,
)


class TrafficService:
    """
    Traffic service coordinator delegating to the active TrafficProvider.
    Defaults to SimulatedTrafficProvider for hackathon robustness and deterministic demo scenarios.
    """

    def __init__(self):
        self.simulated_provider = SimulatedTrafficProvider()
        self.real_provider = RealTrafficProvider()
        self.active_provider: TrafficProvider = self.simulated_provider

    def set_active_provider(self, provider_type: Literal["simulated", "real"]) -> None:
        """Swaps the active provider implementation."""
        if provider_type == "real":
            self.active_provider = self.real_provider
        else:
            self.active_provider = self.simulated_provider

    def get_active_provider_type(self) -> Literal["LIVE", "SIMULATED"]:
        """Returns whether the active provider is LIVE or SIMULATED."""
        return self.active_provider.get_provider_type()

    def set_scenario_mode(self, scenario: Optional[str]) -> None:
        """Injects a demo scenario override ('normal', 'moderate_congestion', 'severe_congestion', 'sudden_anomaly', None)."""
        self.simulated_provider.set_scenario_mode(scenario)

    def get_scenario_mode(self) -> Optional[str]:
        """Returns the currently active demo scenario override if any."""
        return self.simulated_provider.get_scenario_mode()

    def set_online_status(self, is_online: bool) -> None:
        """Allows toggling provider availability for fault-injection testing."""
        self.active_provider.set_online_status(is_online)
        self.simulated_provider.set_online_status(is_online)
        self.real_provider.set_online_status(is_online)

    def is_healthy(self) -> bool:
        """Returns True if the active provider is operational."""
        return self.active_provider.is_healthy()

    def get_route_traffic(
        self,
        coordinates: List[List[float]],
        road_name: str,
        current_hour: Optional[int] = None,
        day_of_week: Optional[int] = None,
        scenario_override: Optional[str] = None,
    ) -> Optional[TrafficTelemetryData]:
        """Retrieves traffic telemetry for a route corridor via the active provider."""
        return self.active_provider.get_route_traffic(
            coordinates=coordinates,
            road_name=road_name,
            current_hour=current_hour,
            day_of_week=day_of_week,
            scenario_override=scenario_override,
        )


# Singleton instance for use across the application
traffic_service = TrafficService()
