"""
Pydantic Schemas

Data transfer models for routing analysis, what-if scenario simulation,
data status monitoring, and health checks in SmartRoute AI.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class RiskFactors(BaseModel):
    """Normalized multi-factor risk scores (0.0 to 1.0)."""
    traffic: float = Field(default=0.0, ge=0.0, le=1.0)
    weather: float = Field(default=0.0, ge=0.0, le=1.0)
    incident: float = Field(default=0.0, ge=0.0, le=1.0)
    road: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_risk: float = Field(default=0.0, ge=0.0, le=1.0)


class IncidentDTO(BaseModel):
    """Standardized incident report with geographic coordinates."""
    incident_id: str
    headline: str
    event_type: str
    severity: str
    location_name: str
    lat: float
    lng: float
    reported_time: str
    affected_route_ids: List[str] = Field(default_factory=list)


class RouteResult(BaseModel):
    """Standardized candidate route output."""
    id: str
    code: str
    name: str
    eta_minutes: int
    distance_km: float
    risk_percent: int
    status: str
    is_recommended: bool
    reliability_score: float
    confidence_score: int
    color: str
    risk_factors: RiskFactors
    data_source: str = "geoapify"  # "here_live" | "geoapify" | "osrm" | "demo"
    overall_score: Optional[float] = None
    predicted_delay_minutes: Optional[float] = None
    delay_prediction_source: Literal["ml", "rule_based"] = "ml"
    explanation_points: List[str] = Field(default_factory=list)
    tradeoff_summary: str = ""
    coordinates: List[List[float]]  # List of [lat, lng] pairs
    is_passable: bool = True
    traffic_anomaly: Optional[Dict[str, Any]] = None
    incidents: List[IncidentDTO] = Field(default_factory=list)
    traffic_status: Optional[str] = None          # "Low" | "Moderate" | "Heavy" — from HERE traffic-aware routing
    traffic_delay_minutes: Optional[float] = None  # positive = congestion delay vs. typical; negative = time saved


class AnalyzeRequest(BaseModel):
    """Payload for analyzing emergency routes between source and destination."""
    source: str = Field(default="Indiranagar, Bengaluru", max_length=200, description="Origin address or lat,lng coordinates")
    destination: str = Field(default="Whitefield, Bengaluru", max_length=200, description="Destination address or lat,lng coordinates")
    vehicle_type: str = Field(default="Ambulance", max_length=50)
    priority: str = Field(default="Critical", max_length=50)

    @field_validator("source", "destination", mode="before")
    @classmethod
    def sanitize_strings(cls, v: Any) -> str:
        if v is None:
            return "Indiranagar, Bengaluru"
        if not isinstance(v, str):
            v = str(v)
        cleaned = v.strip().replace("\x00", "")
        if not cleaned:
            return "Indiranagar, Bengaluru"
        return cleaned[:200]


class MissionProfileDTO(BaseModel):
    """Structured mission profile metadata and optimization weights."""
    key: str
    vehicle_type: str
    priority: str
    profile_label: str
    speed: str
    safety: str
    reliability: str
    accessibility: str
    weights: Dict[str, float]
    description: str


class ConfigureProfileRequest(BaseModel):
    """Payload to configure weights for a specific mission profile."""
    vehicle_type: str = Field(..., min_length=2, max_length=50)
    weights: Dict[str, float]


class AnalyzeResponse(BaseModel):
    """Response payload containing candidate routes and recommended path."""
    recommended_route: str
    routes: List[RouteResult]
    confidence: float = 0.95
    confidence_label: str = "HIGH"
    confidence_percent: int = 95
    explanation: List[str] = Field(default_factory=list)
    alternatives_available: bool = True
    origin_coords: List[float] = Field(default_factory=list)      # [lat, lng]
    destination_coords: List[float] = Field(default_factory=list) # [lat, lng]
    incidents: List[IncidentDTO] = Field(default_factory=list)
    optimization_profile: Optional[MissionProfileDTO] = None
    pipeline_timings_ms: Optional[Dict[str, float]] = None


class SimulateRequest(BaseModel):
    """Payload for what-if scenario stress-testing."""
    source: Optional[str] = Field(default="Indiranagar, Bengaluru", max_length=200)
    destination: Optional[str] = Field(default="Whitefield, Bengaluru", max_length=200)
    vehicle_type: Optional[str] = Field(default="Ambulance", max_length=50)
    priority: Optional[str] = Field(default="Critical", max_length=50)
    rainfall: float = Field(default=0.0, ge=0.0, le=500.0, description="Rainfall intensity in mm")
    traffic_multiplier: float = Field(default=1.0, ge=0.1, le=10.0, description="Traffic surge multiplier")
    road_closure: bool = Field(default=False)
    duration_hours: float = Field(default=1.0, ge=0.1, le=72.0)

    @field_validator("source", "destination", mode="before")
    @classmethod
    def sanitize_sim_strings(cls, v: Any) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("Location must be a string")
        cleaned = v.strip().replace("\x00", "")
        return cleaned or "Indiranagar, Bengaluru"


class SimulatedRouteComparison(BaseModel):
    """Side-by-side comparison between baseline and simulated conditions."""
    id: str
    code: str
    name: str
    current_risk_percent: int
    simulated_risk_percent: int
    current_eta_minutes: int
    simulated_eta_minutes: int
    current_status: str
    simulated_status: str
    is_baseline_recommended: bool
    is_simulated_recommended: bool
    is_passable: bool = True


class SimulateResponse(BaseModel):
    """Response payload containing simulated routes and side-by-side comparisons."""
    baseline_recommended_route: str
    simulated_recommended_route: str
    recommendation_flipped: bool
    comparison: List[SimulatedRouteComparison]
    routes: List[RouteResult]
    confidence: float = 0.94
    confidence_label: str = "HIGH"
    confidence_percent: int = 94
    explanation: List[str] = Field(default_factory=list)
    origin_coords: List[float] = Field(default_factory=list)
    destination_coords: List[float] = Field(default_factory=list)
    incidents: List[IncidentDTO] = Field(default_factory=list)
    optimization_profile: Optional[MissionProfileDTO] = None
    pipeline_timings_ms: Optional[Dict[str, float]] = None


class FeedTelemetryStatus(BaseModel):
    """Detailed live telemetry status, freshness, and provenance for an individual sensor feed."""
    name: str
    source_key: str = "general"
    status: Literal["LIVE", "CACHED", "SIMULATED", "UNAVAILABLE"]
    freshness: Literal["FRESH", "RECENT", "STALE", "UNAVAILABLE"] = "FRESH"
    last_successful_update: Optional[str] = None
    age_seconds: Optional[float] = None
    age_formatted: str = "Unavailable"
    latency_ms: float = 0.0
    last_timestamp: str = ""
    endpoint: str = ""
    source_name: str = ""


class DataStatusResponse(BaseModel):
    """Telemetry sensor feeds health and confidence status."""
    traffic: Literal["live", "unavailable", "cached", "simulated"] = "simulated"
    weather: Literal["live", "unavailable", "cached", "simulated"] = "live"
    news: Literal["live", "unavailable", "cached", "simulated"] = "live"
    maps: Literal["live", "unavailable", "cached", "simulated"] = "live"
    traffic_provider_type: Literal["LIVE", "SIMULATED"] = "SIMULATED"
    traffic_scenario: Optional[str] = None
    confidence: Literal["high", "moderate", "low", "very low"] = "high"
    confidence_percent: int = 95
    feeds_detail: List[FeedTelemetryStatus] = Field(default_factory=list)


class TelemetryLogDTO(BaseModel):
    """Structured audit log entry for external API calls."""
    service_name: str
    endpoint_url: str
    request_status: str
    response_status: Optional[int] = None
    timestamp: str
    latency_ms: float
    provenance: Literal["LIVE", "CACHED", "SIMULATED", "UNAVAILABLE"]
    success: bool
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class TelemetryLogsResponse(BaseModel):
    """List of recent external telemetry audit logs."""
    total_logs: int
    logs: List[TelemetryLogDTO]


class TrafficScenarioRequest(BaseModel):
    """Payload to inject controllable traffic demo scenarios for hackathon presentations."""
    scenario: Optional[Literal["normal", "moderate_congestion", "severe_congestion", "sudden_anomaly"]] = None
    provider: Optional[Literal["simulated", "real"]] = None


class TrafficScenarioResponse(BaseModel):
    """Response reporting the updated traffic provider mode and active scenario."""
    status: str
    provider_type: Literal["LIVE", "SIMULATED"]
    active_scenario: Optional[str] = None
    message: str


class HealthResponse(BaseModel):
    """Service health response."""
    status: str = "ok"


class RootStatusResponse(BaseModel):
    """Root service information and discoverability response."""
    service: str = "SmartRoute AI"
    status: str = "running"
    description: str = "FastAPI Multi-Agent Orchestration Service"
    docs: str = "/docs"
    health: str = "/api/health"


class FaultInjectRequest(BaseModel):
    """Payload for dev/demo fault-injection to test live graceful degradation."""
    source: Literal["traffic", "weather", "news", "maps"]
    enabled: bool  # True = online/live, False = force unavailable


class FaultInjectResponse(BaseModel):
    """Response reporting updated feed availability and confidence score."""
    status: str
    feed_states: dict
    confidence_score: int
    confidence_label: str


class MLModelMetadataResponse(BaseModel):
    """Metadata detailing ML model architecture, training provenance, and synthetic data audit."""
    model_type: str
    features: List[str]
    training_dataset_type: str
    training_sample_count: int
    validation_sample_count: int
    total_dataset_samples: int
    evaluation_metrics: Dict[str, float]
    prediction_sources: List[str]
    live_inference_feeds: List[str]
    synthetic_disclosure: str
    limitations: List[str]


class DemoScenarioInfo(BaseModel):
    """Metadata for a standardized SIH demo scenario."""
    id: str
    number: int
    name: str
    short_title: str
    description: str
    icon: str
    expected_recommended_route: str
    expected_confidence_label: str
    key_features: List[str]


class DemoScenarioListResponse(BaseModel):
    """List of all standardized SIH demo scenarios."""
    scenarios: List[DemoScenarioInfo]
    active_scenario: Optional[str] = None
    is_demo_mode: bool = False


class DemoActivateRequest(BaseModel):
    """Payload to activate a specific SIH demo scenario."""
    scenario_id: str  # "scenario_1" ... "scenario_7"
    vehicle_type: Optional[str] = "Ambulance"
    priority: Optional[str] = "Critical"


class DemoActivateResponse(BaseModel):
    """Response returned when an SIH demo scenario is activated."""
    status: str
    scenario_id: str
    scenario_name: str
    is_demo_data: bool = True
    analyze_result: AnalyzeResponse
    message: str


