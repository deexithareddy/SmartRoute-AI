/**
 * SmartRoute AI - API Service Layer
 *
 * Communicates with FastAPI backend endpoints:
 * - POST /api/analyze
 * - POST /api/simulate
 * - GET /api/data-status
 * - GET /api/health
 */

import axios from 'axios';
import {
  RouteItem,
  RouteResultDTO,
  AnalyzeRequestDTO,
  AnalyzeResponseDTO,
  SimulateRequestDTO,
  SimulateResponseDTO,
  SimulatedRouteComparisonDTO,
  DataStatusResponseDTO,
  HealthResponseDTO,
  DataStatusSummary,
  DataFeedStatus,
  TrafficScenarioRequestDTO,
  TrafficScenarioResponseDTO,
  TelemetryLogsResponseDTO,
  IncidentDTO,
  MissionProfileDTO,
  MLModelMetadataDTO,
  DemoScenarioListResponseDTO,
  DemoActivateResponseDTO,
} from '../types/route';

const API_BASE_URL =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
  'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Maps snake_case backend DTO to frontend RouteItem model
 */
export const mapRouteResultDTOToItem = (dto: RouteResultDTO): RouteItem => {
  return {
    id: dto.id,
    code: dto.code,
    name: dto.name,
    etaMinutes: dto.eta_minutes,
    distanceKm: dto.distance_km,
    riskPercent: dto.risk_percent,
    status: dto.status,
    isRecommended: dto.is_recommended,
    reliabilityScore: dto.reliability_score,
    confidenceScore: dto.confidence_score,
    color: dto.color,
    riskFactors: dto.risk_factors,
    data_source: dto.data_source || 'geoapify',
    trafficStatus: dto.traffic_status,
    trafficDelayMinutes: dto.traffic_delay_minutes,
    overallScore: dto.overall_score,
    predictedDelayMinutes: dto.predicted_delay_minutes,
    delayPredictionSource: dto.delay_prediction_source,
    explanationPoints: dto.explanation_points,
    tradeoffSummary: dto.tradeoff_summary,
    coordinates: dto.coordinates,
    isPassable: dto.is_passable !== undefined ? dto.is_passable : true,
    trafficAnomaly: dto.traffic_anomaly,
    incidents: dto.incidents || [],
  };
};

/**
 * Maps DataStatusResponseDTO to DataStatusSummary
 */
export const mapDataStatusDTOToSummary = (dto: DataStatusResponseDTO): DataStatusSummary => {
  let feeds: DataFeedStatus[] = [];

  if (dto.feeds_detail && dto.feeds_detail.length > 0) {
    feeds = dto.feeds_detail.map((f) => ({
      name: f.name,
      sourceKey: f.source_key,
      status: f.status,
      freshness: f.freshness || 'FRESH',
      lastSuccessfulUpdate: f.last_successful_update,
      ageSeconds: f.age_seconds,
      ageFormatted: f.age_formatted || (f.status === 'UNAVAILABLE' ? 'Unavailable' : 'Updated just now'),
      latencyMs: Math.round(f.latency_ms),
      source: f.source_name,
      lastTimestamp: f.last_timestamp,
      endpoint: f.endpoint,
    }));
  } else {
    const toProv = (st: string): 'LIVE' | 'CACHED' | 'SIMULATED' | 'UNAVAILABLE' => {
      const u = st.toUpperCase();
      if (u === 'LIVE' || u === 'CACHED' || u === 'SIMULATED' || u === 'UNAVAILABLE') {
        return u as any;
      }
      return u === 'LIVE' ? 'LIVE' : 'UNAVAILABLE';
    };

    feeds = [
      {
        name: 'Traffic Feeds',
        sourceKey: 'traffic',
        status: toProv(dto.traffic),
        freshness: toProv(dto.traffic) === 'UNAVAILABLE' ? 'UNAVAILABLE' : 'RECENT',
        ageFormatted: toProv(dto.traffic) === 'UNAVAILABLE' ? 'Unavailable' : 'Updated 18 min ago',
        latencyMs: 24,
        source: 'City Sensor Grid & Flow Telemetry',
      },
      {
        name: 'Weather Radar',
        sourceKey: 'weather',
        status: toProv(dto.weather),
        freshness: toProv(dto.weather) === 'UNAVAILABLE' ? 'UNAVAILABLE' : 'FRESH',
        ageFormatted: toProv(dto.weather) === 'UNAVAILABLE' ? 'Unavailable' : 'Updated 2 min ago',
        latencyMs: 45,
        source: 'Open-Meteo Atmospheric Telemetry',
      },
      {
        name: 'Incident Reports',
        sourceKey: 'news',
        status: toProv(dto.news),
        freshness: toProv(dto.news) === 'UNAVAILABLE' ? 'UNAVAILABLE' : 'FRESH',
        ageFormatted: toProv(dto.news) === 'UNAVAILABLE' ? 'Unavailable' : 'Updated 4 min ago',
        latencyMs: 18,
        source: 'CAD Police & Municipal Feed',
      },
      {
        name: 'Map / Road Network',
        sourceKey: 'maps',
        status: toProv(dto.maps),
        freshness: toProv(dto.maps) === 'UNAVAILABLE' ? 'UNAVAILABLE' : 'FRESH',
        ageFormatted: toProv(dto.maps) === 'UNAVAILABLE' ? 'Unavailable' : 'Updated 1 min ago',
        latencyMs: 65,
        source: 'OSRM & Nominatim Vector Graph',
      },
    ];
  }

  const confidenceTitle =
    dto.confidence.toLowerCase() === 'high'
      ? 'High'
      : dto.confidence.toLowerCase() === 'moderate'
      ? 'Moderate'
      : dto.confidence.toLowerCase() === 'low'
      ? 'Low'
      : 'Very Low';

  const confidencePercent =
    dto.confidence_percent !== undefined
      ? dto.confidence_percent
      : dto.confidence.toLowerCase() === 'high'
      ? 95
      : dto.confidence.toLowerCase() === 'moderate'
      ? 75
      : dto.confidence.toLowerCase() === 'low'
      ? 50
      : 25;

  return {
    feeds,
    confidence: confidenceTitle,
    confidencePercent,
    lastUpdated: 'Just now (Real-time telemetry audit)',
    trafficProviderType: dto.traffic_provider_type || 'SIMULATED',
    trafficScenario: dto.traffic_scenario,
  };
};

export interface RouteAnalysisResult {
  recommendedRouteId: string;
  routes: RouteItem[];
  confidence: number;
  explanation: string[];
  alternativesAvailable: boolean;
  originCoords: [number, number];
  destinationCoords: [number, number];
  incidents: IncidentDTO[];
  optimizationProfile?: MissionProfileDTO;
}

export interface SimulationResult extends RouteAnalysisResult {
  baselineRecommendedRouteId: string;
  simulatedRecommendedRouteId: string;
  recommendationFlipped: boolean;
  comparison: SimulatedRouteComparisonDTO[];
}

export const apiService = {
  /**
   * Health Check: GET /api/health
   */
  getHealth: async (): Promise<HealthResponseDTO> => {
    const response = await apiClient.get<HealthResponseDTO>('/api/health');
    return response.data;
  },

  /**
   * Data Status: GET /api/data-status
   */
  getDataStatus: async (): Promise<DataStatusSummary> => {
    const response = await apiClient.get<DataStatusResponseDTO>('/api/data-status');
    return mapDataStatusDTOToSummary(response.data);
  },

  /**
   * Traffic Scenario Injection: POST /api/traffic/scenario
   */
  setTrafficScenario: async (payload: TrafficScenarioRequestDTO): Promise<TrafficScenarioResponseDTO> => {
    const response = await apiClient.post<TrafficScenarioResponseDTO>('/api/traffic/scenario', payload);
    return response.data;
  },

  /**
   * Telemetry Audit Logs: GET /api/telemetry-logs
   */
  getTelemetryLogs: async (limit: number = 50): Promise<TelemetryLogsResponseDTO> => {
    const response = await apiClient.get<TelemetryLogsResponseDTO>(`/api/telemetry-logs?limit=${limit}`);
    return response.data;
  },

  /**
   * Analyze Routes: POST /api/analyze
   */
  analyzeRoutes: async (payload: AnalyzeRequestDTO): Promise<RouteAnalysisResult> => {
    const response = await apiClient.post<AnalyzeResponseDTO>('/api/analyze', payload);
    const data = response.data;
    return {
      recommendedRouteId: data.recommended_route,
      routes: data.routes.map(mapRouteResultDTOToItem),
      confidence: data.confidence,
      explanation: data.explanation,
      alternativesAvailable: data.alternatives_available,
      originCoords: data.origin_coords || [12.9716, 77.5946],
      destinationCoords: data.destination_coords || [12.9352, 77.6245],
      incidents: data.incidents || [],
      optimizationProfile: data.optimization_profile,
    };
  },

  /**
   * Run Simulation: POST /api/simulate
   */
  simulateScenario: async (payload: SimulateRequestDTO): Promise<SimulationResult> => {
    const response = await apiClient.post<SimulateResponseDTO>('/api/simulate', payload);
    const data = response.data;
    return {
      recommendedRouteId: data.simulated_recommended_route,
      baselineRecommendedRouteId: data.baseline_recommended_route,
      simulatedRecommendedRouteId: data.simulated_recommended_route,
      recommendationFlipped: data.recommendation_flipped,
      comparison: data.comparison || [],
      routes: (data.routes || []).map(mapRouteResultDTOToItem),
      confidence: data.confidence,
      explanation: data.explanation || [],
      alternativesAvailable: true,
      originCoords: data.origin_coords || [12.9716, 77.5946],
      destinationCoords: data.destination_coords || [12.9352, 77.6245],
      incidents: data.incidents || [],
      optimizationProfile: data.optimization_profile,
    };
  },

  /**
   * Fault Injection (Dev / Demo): POST /api/fault-inject
   */
  faultInject: async (source: 'traffic' | 'weather' | 'news' | 'maps', enabled: boolean) => {
    const response = await apiClient.post('/api/fault-inject', { source, enabled });
    return response.data;
  },

  /**
   * Get ML Model Metadata & Audit Details: GET /api/ml/metadata
   */
  getMLMetadata: async (): Promise<MLModelMetadataDTO> => {
    const response = await apiClient.get<MLModelMetadataDTO>('/api/ml/metadata');
    return response.data;
  },

  /**
   * Get SIH Demo Scenarios Catalog: GET /api/demo/scenarios
   */
  getDemoScenarios: async (): Promise<DemoScenarioListResponseDTO> => {
    const response = await apiClient.get<DemoScenarioListResponseDTO>('/api/demo/scenarios');
    return response.data;
  },

  /**
   * Activate SIH Demo Scenario: POST /api/demo/activate
   */
  activateDemoScenario: async (
    scenarioId: string,
    vehicleType: string = 'Ambulance',
    priority: string = 'Critical'
  ): Promise<DemoActivateResponseDTO> => {
    const response = await apiClient.post<DemoActivateResponseDTO>('/api/demo/activate', {
      scenario_id: scenarioId,
      vehicle_type: vehicleType,
      priority: priority,
    });
    return response.data;
  },

  /**
   * Reset Demo Mode: POST /api/demo/reset
   */
  resetDemoMode: async () => {
    const response = await apiClient.post('/api/demo/reset');
    return response.data;
  },
};

export default apiService;
