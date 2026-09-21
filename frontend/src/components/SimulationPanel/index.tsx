import React from 'react';
import { SimulationState, SimulatedRouteComparisonDTO } from '../../types/route';

interface SimulationPanelProps {
  simulationState: SimulationState;
  onChange: (updates: Partial<SimulationState>) => void;
  onSimulate: () => void;
  onReset: () => void;
  isSimulated: boolean;
  isLoading: boolean;
  comparison?: SimulatedRouteComparisonDTO[];
  recommendationFlipped?: boolean;
}

export const SimulationPanel: React.FC<SimulationPanelProps> = ({
  simulationState,
  onChange,
  onSimulate,
  onReset,
  isSimulated,
  isLoading,
  comparison = [],
  recommendationFlipped = false,
}) => {
  // Find current best and simulated best
  const currentBest = comparison.find((c) => c.is_baseline_recommended) || comparison[0];
  const simulatedBest = comparison.find((c) => c.is_simulated_recommended) || comparison[0];

  return (
    <div className="simple-card simulation-card">
      <div className="card-header-simple">
        <span className="card-icon">⚡</span>
        <h3 className="card-title">What-If Simulation</h3>
      </div>

      <div className="simulation-form-body">
        {/* Rainfall Slider */}
        <div className="sim-control-group">
          <div className="sim-label-row">
            <label htmlFor="rainfall-slider" className="sim-label">
              Rainfall:
            </label>
            <span className="sim-val-badge">{simulationState.rainfallMm} mm</span>
          </div>
          <input
            id="rainfall-slider"
            type="range"
            min="0"
            max="100"
            step="5"
            value={simulationState.rainfallMm}
            onChange={(e) => onChange({ rainfallMm: Number(e.target.value) })}
            className="sim-slider"
          />
        </div>

        {/* Traffic Slider */}
        <div className="sim-control-group">
          <div className="sim-label-row">
            <label htmlFor="traffic-slider" className="sim-label">
              Traffic:
            </label>
            <span className="sim-val-badge">{simulationState.trafficMultiplier.toFixed(1)}x</span>
          </div>
          <input
            id="traffic-slider"
            type="range"
            min="1.0"
            max="3.0"
            step="0.1"
            value={simulationState.trafficMultiplier}
            onChange={(e) => onChange({ trafficMultiplier: Number(e.target.value) })}
            className="sim-slider"
          />
        </div>

        {/* Road Closure Toggle */}
        <div className="sim-toggle-row">
          <span className="sim-label">Road Closure:</span>
          <button
            type="button"
            className={`btn-toggle-closure ${simulationState.roadClosure ? 'closure-on' : 'closure-off'}`}
            onClick={() => onChange({ roadClosure: !simulationState.roadClosure })}
          >
            {simulationState.roadClosure ? 'ON (CLOSED)' : 'OFF'}
          </button>
        </div>

        {/* Buttons */}
        <div className="sim-buttons-row">
          <button
            type="button"
            className="btn-simulate-action"
            onClick={onSimulate}
            disabled={isLoading}
          >
            {isLoading ? 'SIMULATING...' : 'SIMULATE'}
          </button>
          {isSimulated && (
            <button
              type="button"
              className="btn-reset-action"
              onClick={onReset}
              disabled={isLoading}
            >
              RESET
            </button>
          )}
        </div>

        {/* Clean Before / After Simulation Result */}
        {isSimulated && currentBest && simulatedBest && (
          <div className="sim-results-box">
            <div className="sim-result-row">
              <span className="result-tag">CURRENT:</span>
              <strong className="result-val">
                {currentBest.code} &mdash; {currentBest.current_risk_percent}% risk
              </strong>
            </div>

            <div className="sim-result-row">
              <span className="result-tag">SIMULATED:</span>
              <strong className="result-val">
                {simulatedBest.code} &mdash; {simulatedBest.simulated_risk_percent}% risk
              </strong>
            </div>

            <div className="sim-result-row sim-rec-row">
              <span className="result-tag tag-new-rec">NEW RECOMMENDATION:</span>
              <strong className="result-winner">
                {simulatedBest.code}
                {recommendationFlipped && ' (Shifted due to disruptions)'}
              </strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimulationPanel;

