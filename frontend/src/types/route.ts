export type RouteStatus =
  | 'BEST'
  | 'LOW'
  | 'MODERATE'
  | 'MEDIUM'
  | 'HIGH'
  | 'SEVERE'
  | 'CRITICAL';

export type VehicleType = 'Ambulance' | 'Medical Supply Truck' | 'Disaster Relief Vehicle';

export type MissionPriority = 'Critical' | 'High' | 'Standard';

export interface RiskFactorScores {
  traffic: number;   // 0.0 - 1.0
  weather: number;   // 0.0 - 1.0
  incident: number;  // 0.0 - 1.0
  road: number;      // 0.0 - 1.0
  overall_risk?: number; // 0.0 - 1.0
}

export interface IncidentDTO {
  incident_id: string;
  headline: string;
  event_type: string;
  severity: string;
  location_name: string;
  lat: number;
  lng: number;
  reported_time: string;
  affected_route_ids?: string[];
}

export interface TrafficAnomalyDTO {
  has_anomaly: boolean;
  severity: string;
  observed_speed?: number;
  expected_speed?: number;
  speed_ratio?: number;
  cause: string;
  explanation: string;
  coordinate?: [number, number];
}

export interface RouteItem {
  id: string;
  code: string; // "Route A", "Route B", "Route C"
  name: string;
  etaMinutes: number;
  distanceKm: number;
  riskPercent: number;
  status: RouteStatus;
  isRecommended: boolean;
  reliabilityScore: number; // 0.0 - 1.0
  confidenceScore: number;  // 0 - 100%
  riskFactors: RiskFactorScores;
  data_source?: string;     // "here_live" | "geoapify" | "osrm" | "demo"
  trafficStatus?: string;   // "Low" | "Moderate" | "Heavy" — from HERE live routing
  trafficDelayMinutes?: number; // positive = congestion delay; negative = faster than typical
  overallScore?: number;
  predictedDelayMinutes?: number;
  delayPredictionSource?: 'ml' | 'rule_based';
  explanationPoints: string[];
  tradeoffSummary: string;
  coordinates: [number, number][];
  color: string;
  isPassable?: boolean;
  trafficAnomaly?: TrafficAnomalyDTO;
  incidents?: IncidentDTO[];
}

export interface RouteInputState {
  source: string;
  destination: string;
  vehicle: VehicleType;
  priority: MissionPriority;
}

export interface SimulationState {
  rainfallMm: number;
  trafficMultiplier: number;
  roadClosure: boolean;
  durationHours?: number;
}

export type FreshnessState = 'FRESH' | 'RECENT' | 'STALE' | 'UNAVAILABLE';

export interface DataFeedStatus {
  name: string;
  sourceKey?: string;
  status: 'LIVE' | 'CACHED' | 'SIMULATED' | 'UNAVAILABLE';
  freshness: FreshnessState;
  lastSuccessfulUpdate?: string;
  ageSeconds?: number;
  ageFormatted: string;
  latencyMs: number;
  source: string;
  lastTimestamp?: string;
  endpoint?: string;
}

export interface DataStatusSummary {
  feeds: DataFeedStatus[];
  confidence: 'High' | 'Moderate' | 'Low' | 'Very Low';
  confidencePercent: number;
  lastUpdated: string;
  trafficProviderType?: 'LIVE' | 'SIMULATED';
  trafficScenario?: string | null;
}

// ==============================================================================
// Backend API DTOs matching schemas.py
// ==============================================================================

export type TrafficScenarioMode = 'normal' | 'moderate_congestion' | 'severe_congestion' | 'sudden_anomaly';

export interface TrafficScenarioRequestDTO {
  scenario?: TrafficScenarioMode | null;
  provider?: 'simulated' | 'real';
}

export interface TrafficScenarioResponseDTO {
  status: string;
  provider_type: 'LIVE' | 'SIMULATED';
  active_scenario?: string | null;
  message: string;
}

export interface RouteResultDTO {
  id: string;
  code: string;
  name: string;
  eta_minutes: number;
  distance_km: number;
  risk_percent: number;
  status: RouteStatus;
  is_recommended: boolean;
  reliability_score: number;
  confidence_score: number;
  color: string;
  risk_factors: RiskFactorScores;
  data_source?: string;
  traffic_status?: string;           // "Low" | "Moderate" | "Heavy" — from HERE live routing
  traffic_delay_minutes?: number;    // positive = congestion delay; negative = faster than typical
  overall_score?: number;
  predicted_delay_minutes?: number;
  delay_prediction_source?: 'ml' | 'rule_based';
  explanation_points: string[];
  tradeoff_summary: string;
  coordinates: [number, number][];
  is_passable?: boolean;
  traffic_anomaly?: TrafficAnomalyDTO;
  incidents?: IncidentDTO[];
}

export interface MissionProfileDTO {
  key: string;
  vehicle_type: string;
  priority: string;
  profile_label: string;
  speed: string;
  safety: string;
  reliability: string;
  accessibility: string;
  weights: Record<string, number>;
  description: string;
}

export interface AnalyzeRequestDTO {
  source: string;
  destination: string;
  vehicle_type: string;
  priority: string;
}

export interface AnalyzeResponseDTO {
  recommended_route: string;
  routes: RouteResultDTO[];
  confidence: number;
  confidence_label?: string;
  confidence_percent?: number;
  explanation: string[];
  alternatives_available: boolean;
  origin_coords: [number, number];
  destination_coords: [number, number];
  incidents?: IncidentDTO[];
  optimization_profile?: MissionProfileDTO;
  pipeline_timings_ms?: Record<string, number>;
}

export interface SimulateRequestDTO {
  source?: string;
  destination?: string;
  vehicle_type?: string;
  priority?: string;
  rainfall: number;
  traffic_multiplier: number;
  road_closure: boolean;
  duration_hours?: number;
}

export interface SimulatedRouteComparisonDTO {
  id: string;
  code: string;
  name: string;
  current_risk_percent: number;
  simulated_risk_percent: number;
  current_eta_minutes: number;
  simulated_eta_minutes: number;
  current_status: string;
  simulated_status: string;
  is_baseline_recommended: boolean;
  is_simulated_recommended: boolean;
  is_passable: boolean;
}

export interface SimulateResponseDTO {
  baseline_recommended_route: string;
  simulated_recommended_route: string;
  recommendation_flipped: boolean;
  comparison: SimulatedRouteComparisonDTO[];
  routes: RouteResultDTO[];
  confidence: number;
  confidence_label?: string;
  confidence_percent?: number;
  explanation: string[];
  origin_coords: [number, number];
  destination_coords: [number, number];
  incidents?: IncidentDTO[];
  optimization_profile?: MissionProfileDTO;
  pipeline_timings_ms?: Record<string, number>;
}

export interface FeedTelemetryStatusDTO {
  name: string;
  source_key?: string;
  status: 'LIVE' | 'CACHED' | 'SIMULATED' | 'UNAVAILABLE';
  freshness: FreshnessState;
  last_successful_update?: string;
  age_seconds?: number;
  age_formatted: string;
  latency_ms: number;
  last_timestamp: string;
  endpoint: string;
  source_name: string;
}

export interface DataStatusResponseDTO {
  traffic: 'live' | 'unavailable' | 'cached' | 'simulated';
  weather: 'live' | 'unavailable' | 'cached' | 'simulated';
  news: 'live' | 'unavailable' | 'cached' | 'simulated';
  maps: 'live' | 'unavailable' | 'cached' | 'simulated';
  traffic_provider_type?: 'LIVE' | 'SIMULATED';
  traffic_scenario?: string | null;
  confidence: 'high' | 'moderate' | 'low' | 'very low';
  confidence_percent?: number;
  feeds_detail?: FeedTelemetryStatusDTO[];
}

export interface TelemetryLogDTO {
  service_name: string;
  endpoint_url: string;
  request_status: string;
  response_status?: number;
  timestamp: string;
  latency_ms: number;
  provenance: 'LIVE' | 'CACHED' | 'SIMULATED' | 'UNAVAILABLE';
  success: boolean;
  error_message?: string;
  details?: Record<string, any>;
}

export interface TelemetryLogsResponseDTO {
  total_logs: number;
  logs: TelemetryLogDTO[];
}

export interface HealthResponseDTO {
  status: string;
}

export interface FaultInjectRequestDTO {
  source: 'traffic' | 'weather' | 'news' | 'maps';
  enabled: boolean;
}

export interface FaultInjectResponseDTO {
  status: string;
  feed_states: {
    traffic: boolean;
    weather: boolean;
    news: boolean;
    maps: boolean;
  };
  confidence_score: number;
  confidence_label: string;
}

export interface MLModelMetadataDTO {
  model_type: string;
  features: string[];
  training_dataset_type: string;
  training_sample_count: number;
  validation_sample_count: number;
  total_dataset_samples: number;
  evaluation_metrics: Record<string, number>;
  prediction_sources: string[];
  live_inference_feeds: string[];
  synthetic_disclosure: string;
  limitations: string[];
}

export interface DemoScenarioInfoDTO {
  id: string;
  number: number;
  name: string;
  short_title: string;
  description: string;
  icon: string;
  expected_recommended_route: string;
  expected_confidence_label: string;
  key_features: string[];
}

export interface DemoScenarioListResponseDTO {
  scenarios: DemoScenarioInfoDTO[];
  active_scenario?: string | null;
  is_demo_mode: boolean;
}

export interface DemoActivateRequestDTO {
  scenario_id: string;
  vehicle_type?: string;
  priority?: string;
}

export interface DemoActivateResponseDTO {
  status: string;
  scenario_id: string;
  scenario_name: string;
  is_demo_data: boolean;
  analyze_result: AnalyzeResponseDTO;
  message: string;
}
