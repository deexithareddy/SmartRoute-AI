import React, { useState, useCallback } from 'react';
import { RouteInput } from '../components/RouteInput';
import { Map } from '../components/Map';
import { RiskPanel } from '../components/RiskPanel';
import { RouteCard } from '../components/RouteCard';
import { ExplanationPanel } from '../components/ExplanationPanel';
import { DataStatus } from '../components/DataStatus';
import { SimulationPanel } from '../components/SimulationPanel';

import {
  RouteItem,
  RouteInputState,
  SimulationState,
  SimulatedRouteComparisonDTO,
  DataStatusSummary,
  IncidentDTO,
} from '../types/route';
import {
  BASELINE_ROUTES,
  INITIAL_DATA_STATUS,
  LOCATION_ORIGIN,
  LOCATION_DESTINATION,
} from '../mock/mockRoutes';
import { apiService } from '../services/api';

export const Dashboard: React.FC = () => {
  // 1. Route Input State
  const [inputState, setInputState] = useState<RouteInputState>({
    source: LOCATION_ORIGIN.name,
    destination: LOCATION_DESTINATION.name,
    vehicle: 'Ambulance',
    priority: 'Critical',
  });

  // 2. GIS Coordinates & Telemetry
  const [originCoords, setOriginCoords] = useState<[number, number]>(LOCATION_ORIGIN.coords);
  const [destinationCoords, setDestinationCoords] = useState<[number, number]>(LOCATION_DESTINATION.coords);

  // 3. Simulation State
  const [simulationState, setSimulationState] = useState<SimulationState>({
    rainfallMm: 45,
    trafficMultiplier: 1.5,
    roadClosure: true,
  });
  const [simComparison, setSimComparison] = useState<SimulatedRouteComparisonDTO[]>([]);
  const [recFlipped, setRecFlipped] = useState<boolean>(false);
  const [isSimulated, setIsSimulated] = useState<boolean>(false);

  // 4. Data Confidence Status State
  const [dataStatus, setDataStatus] = useState<DataStatusSummary>(INITIAL_DATA_STATUS);

  // 5. Active Pipeline State
  const [routes, setRoutes] = useState<RouteItem[]>([]);
  const [incidents, setIncidents] = useState<IncidentDTO[]>([]);
  const [systemExplanation, setSystemExplanation] = useState<string[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [userError, setUserError] = useState<string | null>(null);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);

  // Derived current recommended & selected routes
  const recommendedRoute = routes.find((r) => r.isRecommended) || routes[0];

  // Handle Input Updates
  const handleInputChange = (updates: Partial<RouteInputState>) => {
    setInputState((prev) => ({ ...prev, ...updates }));
  };

  // Handle Simulation Parameter Updates
  const handleSimulationChange = (updates: Partial<SimulationState>) => {
    setSimulationState((prev) => ({ ...prev, ...updates }));
  };

  // Execute POST /api/analyze (Real Geoapify Routing & Geocoding)
  const executeAnalyze = useCallback(async () => {
    setIsAnalyzing(true);
    setUserError(null);
    try {
      const result = await apiService.analyzeRoutes({
        source: inputState.source,
        destination: inputState.destination,
        vehicle_type: inputState.vehicle,
        priority: inputState.priority,
      });

      setIsSimulated(false);
      setIsDemoMode(false);
      setSimComparison([]);
      setRecFlipped(false);
      setRoutes(result.routes);
      setIncidents(result.incidents || []);
      setSystemExplanation(result.explanation || []);
      if (result.originCoords) setOriginCoords(result.originCoords);
      if (result.destinationCoords) setDestinationCoords(result.destinationCoords);
      setSelectedRouteId(result.recommendedRouteId || (result.routes[0]?.id ?? ''));
    } catch (err: any) {
      console.warn('API analyze call notice:', err);
      // Requirement 6: Zero silent dummy fallback on live failure. Clear routes and show real error.
      setRoutes([]);
      setSelectedRouteId('');
      const errorDetail =
        err?.response?.data?.detail ||
        err?.message ||
        'Unable to calculate live routes for the specified locations. Please check the address or connectivity.';
      setUserError(errorDetail);
    } finally {
      setIsAnalyzing(false);
    }
  }, [inputState]);

  // Load Demo / Simulated Dataset (Explicit Mode)
  const loadDemoMode = () => {
    setIsDemoMode(true);
    setUserError(null);
    setRoutes(BASELINE_ROUTES);
    setOriginCoords(LOCATION_ORIGIN.coords);
    setDestinationCoords(LOCATION_DESTINATION.coords);
    setSelectedRouteId('route-b');
  };

  // Execute POST /api/simulate
  const executeSimulate = async () => {
    setIsSimulating(true);
    setUserError(null);
    try {
      const result = await apiService.simulateScenario({
        source: inputState.source,
        destination: inputState.destination,
        vehicle_type: inputState.vehicle,
        priority: inputState.priority,
        rainfall: simulationState.rainfallMm,
        traffic_multiplier: simulationState.trafficMultiplier,
        road_closure: simulationState.roadClosure,
        duration_hours: 1.0,
      });

      setIsSimulated(true);
      setRoutes(result.routes);
      setIncidents(result.incidents || []);
      setSystemExplanation(result.explanation || []);
      setSimComparison(result.comparison || []);
      setRecFlipped(result.recommendationFlipped || false);
      if (result.originCoords) setOriginCoords(result.originCoords);
      if (result.destinationCoords) setDestinationCoords(result.destinationCoords);
      setSelectedRouteId(result.recommendedRouteId || (result.routes[0]?.id ?? ''));
    } catch (err: any) {
      console.warn('API simulate call notice:', err);
      const errorDetail =
        err?.response?.data?.detail ||
        err?.message ||
        'Simulation completed with estimated scenario adjustments.';
      setUserError(errorDetail);
    } finally {
      setIsSimulating(false);
    }
  };

  // Reset Simulation back to live baseline
  const resetSimulation = () => {
    setIsSimulated(false);
    setSimComparison([]);
    setRecFlipped(false);
    executeAnalyze();
  };

  // Initial load on mount
  React.useEffect(() => {
    executeAnalyze();
    apiService.getDataStatus().then(setDataStatus).catch(console.warn);
  }, [executeAnalyze]);

  return (
    <div className="simple-dashboard-root">
      {/* HEADER */}
      <header className="simple-header">
        <div className="header-brand-box">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <h1 className="app-main-title">SMARTROUTE AI</h1>
            <span
              className="region-badge-pill"
              style={{
                background: 'rgba(56, 189, 248, 0.15)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.35)',
                padding: '0.2rem 0.65rem',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                fontWeight: '700',
                letterSpacing: '0.04em',
              }}
            >
              Operational Region: Hyderabad
            </span>
          </div>
          <span className="app-tagline">Hyderabad Emergency Route Intelligence</span>
        </div>
        <div className="header-status-box">
          {isDemoMode ? (
            <span className="online-indicator-pill" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', borderColor: 'rgba(59, 130, 246, 0.3)' }}>
              <span className="online-dot" style={{ backgroundColor: '#60a5fa', boxShadow: '0 0 8px #60a5fa' }}></span>
              DEMO / SIMULATED DATA
            </span>
          ) : routes.length > 0 ? (
            <span className="online-indicator-pill">
              <span className="online-dot"></span>
              LIVE GEOAPIFY ROUTING (HYDERABAD)
            </span>
          ) : (
            <span className="online-indicator-pill">
              <span className="online-dot"></span>
              System Online
            </span>
          )}
        </div>
      </header>

      {/* User-Friendly Error Banner with Demo Mode Recovery */}
      {userError && (
        <div className="user-alert-banner">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span>⚠️ {userError}</span>
            <button
              type="button"
              className="btn-demo-mode-pill"
              onClick={loadDemoMode}
              style={{
                background: 'rgba(59, 130, 246, 0.2)',
                color: '#93c5fd',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                padding: '0.25rem 0.6rem',
                borderRadius: '4px',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                cursor: 'pointer',
              }}
            >
              🧪 Load Demo Dataset
            </button>
          </div>
          <button
            type="button"
            className="btn-alert-dismiss"
            onClick={() => setUserError(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* MAIN CONTENT GRID */}
      <main className="dashboard-grid">
        {/* Top Section: Route Input (Left) & Large Interactive Map (Right) */}
        <section className="section-top-row">
          <div className="col-input">
            <RouteInput
              inputState={inputState}
              onChange={handleInputChange}
              onAnalyze={executeAnalyze}
              isLoading={isAnalyzing}
            />
          </div>

          <div className="col-map">
            <Map
              routes={routes}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
              originCoords={originCoords}
              destinationCoords={destinationCoords}
              originName={inputState.source}
              destinationName={inputState.destination}
              incidents={incidents}
            />
          </div>
        </section>

        {/* Middle Section: Recommended Route Card & Why This Route */}
        <section className="section-insights-row">
          <div className="col-rec-card">
            <RiskPanel recommendedRoute={recommendedRoute} />
          </div>

          <div className="col-why-card">
            <ExplanationPanel
              recommendedRoute={recommendedRoute}
              allRoutes={routes}
              systemExplanation={systemExplanation}
            />
          </div>
        </section>

        {/* Section 4: Route Comparison Table */}
        <section className="section-comparison-row">
          <RouteCard
            routes={routes}
            selectedRouteId={selectedRouteId}
            onSelectRoute={setSelectedRouteId}
          />
        </section>

        {/* Bottom Section: Data Confidence & What-If Simulation */}
        <section className="section-bottom-row">
          <div className="col-confidence">
            <DataStatus statusData={dataStatus} />
          </div>

          <div className="col-simulation">
            <SimulationPanel
              simulationState={simulationState}
              onChange={handleSimulationChange}
              onSimulate={executeSimulate}
              onReset={resetSimulation}
              isSimulated={isSimulated}
              isLoading={isSimulating}
              comparison={simComparison}
              recommendationFlipped={recFlipped}
            />
          </div>
        </section>
      </main>
    </div>
  );
};

export default Dashboard;
