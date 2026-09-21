import React from 'react';
import { VehicleType, MissionPriority, RouteInputState } from '../../types/route';

interface RouteInputProps {
  inputState: RouteInputState;
  onChange: (updates: Partial<RouteInputState>) => void;
  onAnalyze: () => void;
  isLoading: boolean;
}

export const RouteInput: React.FC<RouteInputProps> = ({
  inputState,
  onChange,
  onAnalyze,
  isLoading,
}) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAnalyze();
  };

  return (
    <div className="simple-card route-input-card">
      <div className="card-header-simple">
        <span className="card-icon">📍</span>
        <h3 className="card-title">Route Parameters</h3>
      </div>

      <form onSubmit={handleSubmit} className="simple-form">
        <div className="form-group">
          <label htmlFor="source-input" className="form-label">
            Source Location
          </label>
          <input
            id="source-input"
            type="text"
            className="simple-input"
            value={inputState.source}
            onChange={(e) => onChange({ source: e.target.value })}
            placeholder="e.g. Rajiv Gandhi International Airport, Hyderabad"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="destination-input" className="form-label">
            Destination
          </label>
          <input
            id="destination-input"
            type="text"
            className="simple-input"
            value={inputState.destination}
            onChange={(e) => onChange({ destination: e.target.value })}
            placeholder="e.g. Secunderabad Railway Station, Hyderabad"
            required
          />
        </div>

        <div className="form-row-2">
          <div className="form-group">
            <label htmlFor="vehicle-select" className="form-label">
              Vehicle
            </label>
            <select
              id="vehicle-select"
              className="simple-select"
              value={inputState.vehicle}
              onChange={(e) => onChange({ vehicle: e.target.value as VehicleType })}
            >
              <option value="Ambulance">🚑 Ambulance</option>
              <option value="Medical Supply Truck">🚚 Medical Supply Truck</option>
              <option value="Disaster Relief Vehicle">🚜 Disaster Relief Vehicle</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="priority-select" className="form-label">
              Priority
            </label>
            <select
              id="priority-select"
              className="simple-select"
              value={inputState.priority}
              onChange={(e) => onChange({ priority: e.target.value as MissionPriority })}
            >
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Standard">Standard</option>
            </select>
          </div>
        </div>

        <button
          type="submit"
          className="btn-analyze"
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="btn-loading-content">
              <span className="spinner-mini"></span>
              ANALYZING ROUTE...
            </span>
          ) : (
            'ANALYZE ROUTE'
          )}
        </button>
      </form>
    </div>
  );
};

export default RouteInput;

