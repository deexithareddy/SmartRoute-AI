/**
 * SmartRoute AI - Domain Types and Schema Definitions
 */

export interface Coordinates {
  lat: number;
  lng: number;
}

export interface RiskBreakdown {
  traffic_risk: number;
  weather_risk: number;
  incident_risk: number;
  road_risk: number;
  overall_risk: number;
}

export interface RouteSegment {
  segment_id: string;
  distance_meters: number;
  duration_seconds: number;
  speed_limit_kmh?: number;
  observed_speed_kmh?: number;
  risk_breakdown?: RiskBreakdown;
}

export interface Route {
  route_id: string;
  name: string;
  summary: string;
  total_distance_km: number;
  estimated_duration_minutes: number;
  predicted_delay_minutes: number;
  reliability_score: number;
  overall_score: number;
  risk_breakdown: RiskBreakdown;
  geometry?: [number, number][];
  segments: RouteSegment[];
  explanation?: string;
  is_recommended: boolean;
}

export interface AnalyzeRequest {
  origin: Coordinates;
  destination: Coordinates;
  vehicle_type: 'ambulance' | 'supply_truck' | 'relief_vehicle';
  mission_priority: 'speed_and_safety' | 'fastest' | 'highest_reliability';
}

export interface AnalyzeResponse {
  routes: Route[];
  recommended_route_id: string;
  decision_summary: string;
  timestamp: string;
}

export interface SimulationRequest {
  base_route_id?: string;
  traffic_surge_percent: number;
  rainfall_increase_mm: number;
  closed_segments: string[];
}

export interface DataStatusInfo {
  traffic_feed_status: 'HEALTHY' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN';
  weather_feed_status: 'HEALTHY' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN';
  incident_feed_status: 'HEALTHY' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN';
  last_updated?: string;
  confidence_level: number;
}
