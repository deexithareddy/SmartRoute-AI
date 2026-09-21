import React, { useState } from 'react';
import { AnalyzeResponseDTO } from '../../types/route';
import apiService from '../../services/api';

interface DemoModeBarProps {
  onScenarioActivated: (result: AnalyzeResponseDTO, scenarioTitle: string) => void;
  onResetLiveMode: () => void;
  onLaunchFullDemoTour?: () => void;
  activeScenarioId?: string | null;
  activeVehicleType?: string;
  activePriority?: string;
}

const DEMO_SCENARIO_BUTTONS: Array<{
  id: string;
  num: number;
  label: string;
  icon: string;
  tooltip: string;
}> = [
  { id: 'scenario_1', num: 1, label: '1. Normal', icon: '🟢', tooltip: 'Clear weather, free-flow traffic, Route A fastest & recommended' },
  { id: 'scenario_2', num: 2, label: '2. Traffic Anomaly', icon: '🔴', tooltip: 'Severe speed drop on Route A (Cause: UNKNOWN) -> Route B recommended' },
  { id: 'scenario_3', num: 3, label: '3. Heavy Rain', icon: '🌧️', tooltip: '45 mm/h downpour -> Elevated Route B recommended over flooded Route A' },
  { id: 'scenario_4', num: 4, label: '4. CAD Incident', icon: '🚨', tooltip: 'Confirmed police accident on Route A -> Route B circumvents hazard' },
  { id: 'scenario_5', num: 5, label: '5. Road Closure', icon: '⛔', tooltip: 'Route A marked CLOSED/Impassable -> Route B sole surviving corridor' },
  { id: 'scenario_6', num: 6, label: '6. Traffic Offline', icon: '⚡', tooltip: 'Traffic feed cut -> 75% Moderate confidence & Rule-Based Fallback' },
  { id: 'scenario_7', num: 7, label: '7. Single Route', icon: '🛣️', tooltip: 'Single physical corridor -> Honest zero-hallucination warning banner' },
];

export const DemoModeBar: React.FC<DemoModeBarProps> = ({
  onScenarioActivated,
  onResetLiveMode,
  onLaunchFullDemoTour,
  activeScenarioId,
  activeVehicleType = 'Ambulance',
  activePriority = 'Critical',
}) => {
  const [loadingScenario, setLoadingScenario] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  // Check if build allows demo mode (default true in Vite dev & staging)
  const isDemoBuild = import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEMO_MODE !== 'false';
  if (!isDemoBuild) return null;

  const handleSelectScenario = async (scenarioId: string) => {
    try {
      setLoadingScenario(scenarioId);
      const res = await apiService.activateDemoScenario(scenarioId, activeVehicleType, activePriority);
      if (res && res.analyze_result) {
        onScenarioActivated(res.analyze_result, res.scenario_name);
      }
    } catch (err) {
      console.error('Error activating SIH demo scenario:', err);
    } finally {
      setLoadingScenario(null);
    }
  };

  const handleReset = async () => {
    try {
      setLoadingScenario('reset');
      await apiService.resetDemoMode();
      onResetLiveMode();
    } catch (err) {
      console.error('Error resetting demo mode:', err);
    } finally {
      setLoadingScenario(null);
    }
  };

  const activeScenarioObj = DEMO_SCENARIO_BUTTONS.find((s) => s.id === activeScenarioId);

  return (
    <div className={`demo-mode-bar-container ${activeScenarioId ? 'is-active-demo' : ''}`}>
      <div className="demo-bar-header">
        <div className="demo-bar-title-group">
          <span className="demo-live-badge">🏆 SIH JURY DEMO SUITE</span>
          <span className="demo-data-pill">DEMO DATA</span>
          {activeScenarioObj ? (
            <span className="demo-active-scenario-tag">
              Active: {activeScenarioObj.icon} {activeScenarioObj.label}
            </span>
          ) : (
            <span className="demo-idle-tag">Live Telemetry Mode Active</span>
          )}
        </div>

        <div className="demo-bar-actions">
          {onLaunchFullDemoTour && (
            <button
              type="button"
              className="demo-full-tour-btn"
              onClick={onLaunchFullDemoTour}
              title="Launch automated 12-step guided demo tour for SIH jury"
            >
              🎬 Run Full Demo
            </button>
          )}
          <button
            type="button"
            className="demo-toggle-expand-btn"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? '▲ Hide Scenarios' : '▼ Select Demo Scenario'}
          </button>
          {activeScenarioId && (
            <button
              type="button"
              className="demo-reset-btn"
              onClick={handleReset}
              disabled={loadingScenario !== null}
            >
              ↺ Reset to Live Pipeline
            </button>
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="demo-bar-body">
          <div className="demo-scenarios-scroll">
            {DEMO_SCENARIO_BUTTONS.map((sc) => {
              const isSelected = activeScenarioId === sc.id;
              const isLoading = loadingScenario === sc.id;

              return (
                <button
                  key={sc.id}
                  type="button"
                  className={`demo-scenario-chip ${isSelected ? 'active' : ''}`}
                  onClick={() => handleSelectScenario(sc.id)}
                  disabled={loadingScenario !== null}
                  title={sc.tooltip}
                >
                  <span className="chip-icon">{sc.icon}</span>
                  <span className="chip-label">{sc.label}</span>
                  {isLoading && <span className="chip-spinner">...</span>}
                </button>
              );
            })}
          </div>

          {activeScenarioObj && (
            <div className="demo-active-callout">
              <span className="callout-icon">💡</span>
              <span className="callout-text">
                <strong>Deterministic Demo State:</strong> {activeScenarioObj.tooltip}. Labeled as{' '}
                <span className="callout-demo-label">DEMO DATA</span> with multi-factor risk and explainability recalibrated.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DemoModeBar;
