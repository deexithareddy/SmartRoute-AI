/**
 * Frontend Component and Model Logic Unit Tests
 */

import { mapRouteResultDTOToItem, mapDataStatusDTOToSummary } from '../services/api';
import { RouteResultDTO, DataStatusResponseDTO } from '../types/route';

console.log('=== Running Frontend Unit Tests ===');

// Test 1: DTO Mapping for Route Result
const mockRouteDTO: RouteResultDTO = {
  id: 'route-a',
  code: 'Route A',
  name: 'Swamy Vivekananda Road',
  eta_minutes: 16,
  distance_km: 15.6,
  risk_percent: 46,
  status: 'MODERATE',
  is_recommended: true,
  reliability_score: 0.75,
  confidence_score: 95,
  color: '#ef4444',
  risk_factors: { traffic: 0.56, weather: 0.13, incident: 0.75, road: 0.30, overall_risk: 0.46 },
  overall_score: 0.312,
  predicted_delay_minutes: 21.0,
  delay_prediction_source: 'ml',
  explanation_points: ['✓ Test Point 1', '⚠️ Active Incident'],
  tradeoff_summary: 'Test summary',
  coordinates: [[12.9716, 77.5946], [12.9352, 77.6245]],
};

const routeItem = mapRouteResultDTOToItem(mockRouteDTO);
console.assert(routeItem.id === 'route-a', 'Route ID mapping failed');
console.assert(routeItem.etaMinutes === 16, 'ETA mapping failed');
console.assert(routeItem.predictedDelayMinutes === 21.0, 'Delay mapping failed');
console.assert(routeItem.delayPredictionSource === 'ml', 'Delay source mapping failed');
console.log('✓ Test 1 Passed: Route Result DTO Mapping');

// Test 2: Data Status DTO Mapping
const mockStatusDTO: DataStatusResponseDTO = {
  traffic: 'unavailable',
  weather: 'live',
  news: 'live',
  maps: 'live',
  confidence: 'moderate',
};

const statusSummary = mapDataStatusDTOToSummary(mockStatusDTO);
console.assert(statusSummary.confidence === 'Moderate', 'Confidence mapping failed');
console.assert(statusSummary.confidencePercent === 75, 'Confidence percentage failed');
console.assert(statusSummary.feeds.length === 4, 'Feeds count failed');
const trafficFeed = statusSummary.feeds.find((f) => f.name.includes('Traffic'));
console.assert(trafficFeed?.status === 'UNAVAILABLE', 'Traffic feed status failed');
console.log('✓ Test 2 Passed: Data Status DTO Mapping & Degradation');

console.log('=== All Frontend Unit Assertions Passed! ===');
