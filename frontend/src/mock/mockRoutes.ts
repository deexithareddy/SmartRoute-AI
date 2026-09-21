import { RouteItem, DataStatusSummary } from '../types/route';

export const HYDERABAD_CENTER: [number, number] = [17.3850, 78.4867];
export const MAP_CENTER: [number, number] = [17.3850, 78.4867];
export const DEFAULT_MAP_ZOOM = 11.5;
export const OPERATIONAL_REGION = "Hyderabad";

export const LOCATION_ORIGIN = {
  name: "Hyderabad",
  address: "Hyderabad, Telangana, India",
  coords: [17.3850, 78.4867] as [number, number],
};

export const LOCATION_DESTINATION = {
  name: "Secunderabad",
  address: "Secunderabad, Telangana, India",
  coords: [17.4399, 78.4983] as [number, number],
};

// Baseline routes (Demo / Simulated Dataset for Hyderabad)
export const BASELINE_ROUTES: RouteItem[] = [
  {
    id: "route-a",
    code: "Route A",
    name: "Charminar Road via NH765",
    etaMinutes: 13,
    distanceKm: 12.2,
    riskPercent: 16,
    status: "BEST",
    isRecommended: true,
    reliabilityScore: 0.86,
    confidenceScore: 95,
    color: "#10b981", // Emerald
    data_source: "demo",
    riskFactors: {
      traffic: 0.24,
      weather: 0.10,
      incident: 0.0,
      road: 0.15,
      overall_risk: 0.16,
    },
    overallScore: 0.094,
    predictedDelayMinutes: 4.3,
    delayPredictionSource: 'ml',
    isPassable: true,
    tradeoffSummary: "Fastest nominal ETA (13 min) with low traffic congestion and zero emergency disruptions.",
    explanationPoints: [
      "✓ Fastest candidate corridor (13 min nominal ETA)",
      "✓ Low traffic congestion risk (24% congestion exposure)",
      "✓ No reported incidents or emergency lane blockages",
      "✓ 86% arrival certainty under current traffic telemetry"
    ],
    coordinates: [
      [17.3606, 78.4741],
      [17.3850, 78.4867],
      [17.4100, 78.4920],
      [17.4337, 78.5007],
    ],
  },
  {
    id: "route-b",
    code: "Route B",
    name: "Inner Ring Road via Amberpet",
    etaMinutes: 16,
    distanceKm: 10.7,
    riskPercent: 16,
    status: "LOW",
    isRecommended: false,
    reliabilityScore: 0.86,
    confidenceScore: 95,
    color: "#38bdf8", // Cyan
    data_source: "demo",
    riskFactors: {
      traffic: 0.26,
      weather: 0.10,
      incident: 0.0,
      road: 0.15,
      overall_risk: 0.16,
    },
    overallScore: 0.239,
    predictedDelayMinutes: 4.5,
    delayPredictionSource: 'ml',
    isPassable: true,
    tradeoffSummary: "Shorter physical distance (10.7 km) but slightly higher junction signals adding +3 min nominal delay.",
    explanationPoints: [
      "✓ Shorter physical distance (10.7 km vs 12.2 km)",
      "⚠️ Slightly slower nominal travel time (+3 min compared to Route A)",
      "✓ Free flowing secondary arterial with zero lane disruptions"
    ],
    coordinates: [
      [17.3606, 78.4741],
      [17.3900, 78.5100],
      [17.4200, 78.5150],
      [17.4337, 78.5007],
    ],
  },
  {
    id: "route-c",
    code: "Route C",
    name: "Nehru ORR Bypass Corridor",
    etaMinutes: 24,
    distanceKm: 28.5,
    riskPercent: 25,
    status: "MODERATE",
    isRecommended: false,
    reliabilityScore: 0.82,
    confidenceScore: 92,
    color: "#f59e0b", // Amber
    data_source: "demo",
    riskFactors: {
      traffic: 0.18,
      weather: 0.35,
      incident: 0.0,
      road: 0.20,
      overall_risk: 0.25,
    },
    overallScore: 0.45,
    predictedDelayMinutes: 5.2,
    delayPredictionSource: 'ml',
    isPassable: true,
    tradeoffSummary: "Expressway orbital bypass with continuous 80 km/h speed, but +11 min longer due to perimeter detour.",
    explanationPoints: [
      "✓ Uninterrupted high-speed expressway grade separation (80 km/h)",
      "⚠️ Perimeter detour increases travel distance to 28.5 km (+11 min)",
      "✓ Resilient fallback corridor if central city arterial suffers gridlock"
    ],
    coordinates: [
      [17.3606, 78.4741],
      [17.3300, 78.4300],
      [17.3800, 78.3800],
      [17.4500, 78.4300],
      [17.4337, 78.5007],
    ],
  },
];

// Simulated routes (Hypothetical Storm & Road Closure scenario)
export const SIMULATED_ROUTES: RouteItem[] = [
  {
    id: "route-a",
    code: "Route A",
    name: "Direct Arterial (MG / Hosur Rd)",
    etaMinutes: 52,
    distanceKm: 8.4,
    riskPercent: 92,
    status: "CRITICAL",
    isRecommended: false,
    reliabilityScore: 0.28,
    confidenceScore: 85,
    color: "#e11d48", // Crimson
    riskFactors: {
      traffic: 0.98,
      weather: 0.88,
      incident: 0.95,
      road: 0.85,
    },
    tradeoffSummary: "IMPASSABLE / CRITICAL: Flash flooding in underpass combined with +50% traffic surge makes this route non-viable.",
    explanationPoints: [
      "⛔ CRITICAL HAZARD: Water level in Richmond underpass exceeds vehicle safety clearance",
      "⛔ Gridlock: Traffic surge +50% caused complete standstill on arterial junction",
      "⚠️ Delay risk +26 minutes over baseline ETA",
      "⚠️ Severe risk of ambulance immobilization"
    ],
    coordinates: [
      [12.9716, 77.5946],
      [12.9680, 77.5980],
      [12.9610, 77.6030],
      [12.9550, 77.6090],
      [12.9480, 77.6150],
      [12.9410, 77.6200],
      [12.9352, 77.6245],
    ],
  },
  {
    id: "route-b",
    code: "Route B",
    name: "Elevated Expressway Corridor",
    etaMinutes: 44,
    distanceKm: 11.2,
    riskPercent: 58,
    status: "HIGH",
    isRecommended: false,
    reliabilityScore: 0.65,
    confidenceScore: 92,
    color: "#f97316", // Orange
    riskFactors: {
      traffic: 0.68,
      weather: 0.55,
      incident: 0.40,
      road: 0.35,
    },
    tradeoffSummary: "Spillover bottleneck: Heavy congestion at elevated access ramps increases risk and adds +13 min delay.",
    explanationPoints: [
      "⚠️ Significant bottleneck: Diverted city traffic is queuing at expressway on-ramps",
      "⚠️ High crosswinds on elevated viaduct (>45 km/h) requiring speed reduction",
      "✓ Deck surface remains free of standing water",
      "⚠️ ETA increased from 31m to 44m due to simulated traffic surge"
    ],
    coordinates: [
      [12.9716, 77.5946],
      [12.9740, 77.6050],
      [12.9700, 77.6180],
      [12.9600, 77.6260],
      [12.9490, 77.6280],
      [12.9400, 77.6260],
      [12.9352, 77.6245],
    ],
  },
  {
    id: "route-c",
    code: "Route C",
    name: "Outer Ring Orbital Bypass",
    etaMinutes: 37,
    distanceKm: 14.8,
    riskPercent: 28,
    status: "BEST",
    isRecommended: true,
    reliabilityScore: 0.91,
    confidenceScore: 94,
    color: "#10b981", // Emerald (Now BEST)
    riskFactors: {
      traffic: 0.22,
      weather: 0.35,
      incident: 0.15,
      road: 0.20,
    },
    tradeoffSummary: "RECOMMENDED UNDER SIMULATION: Orbital bypass completely circumvents flooded central bottlenecks with highest reliability.",
    explanationPoints: [
      "✓ BEST CHOICE: Fully open orbital bypass with wide shoulders and high-capacity drainage",
      "✓ Traffic surge has not propagated to peripheral ring roads",
      "✓ Now 7 minutes FASTER than Route B and 15 minutes faster than Route A",
      "✓ 91% arrival certainty under 45mm simulated rainfall"
    ],
    coordinates: [
      [12.9716, 77.5946],
      [12.9620, 77.5850],
      [12.9480, 77.5880],
      [12.9380, 77.5980],
      [12.9320, 77.6110],
      [12.9352, 77.6245],
    ],
  },
];

export const INITIAL_DATA_STATUS: DataStatusSummary = {
  feeds: [
    {
      name: "Weather Radar",
      sourceKey: "weather",
      status: "LIVE",
      freshness: "FRESH",
      ageFormatted: "Updated 2 min ago",
      latencyMs: 45,
      source: "Open-Meteo Atmospheric Telemetry",
    },
    {
      name: "Traffic Feeds",
      sourceKey: "traffic",
      status: "CACHED",
      freshness: "RECENT",
      ageFormatted: "Updated 18 min ago",
      latencyMs: 24,
      source: "City Sensor Grid & Flow Telemetry",
    },
    {
      name: "Incident Reports",
      sourceKey: "news",
      status: "LIVE",
      freshness: "FRESH",
      ageFormatted: "Updated 4 min ago",
      latencyMs: 18,
      source: "CAD Dispatch, Police & Municipal Feed",
    },
    {
      name: "Map / Road Network",
      sourceKey: "maps",
      status: "LIVE",
      freshness: "FRESH",
      ageFormatted: "Updated 1 min ago",
      latencyMs: 65,
      source: "OSRM High-Precision Vector Graph",
    },
  ],
  confidence: "High",
  confidencePercent: 94,
  lastUpdated: "Just now (Live streaming)",
};
