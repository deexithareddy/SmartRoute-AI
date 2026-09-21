import React from 'react';
import { RouteItem } from '../../types/route';

interface RouteCardProps {
  routes: RouteItem[];
  selectedRouteId: string;
  onSelectRoute: (id: string) => void;
}

// Traffic status display helpers
const TRAFFIC_CONFIG: Record<string, { icon: string; color: string }> = {
  Low:      { icon: '🟢', color: '#10b981' },
  Moderate: { icon: '🟡', color: '#f59e0b' },
  Heavy:    { icon: '🔴', color: '#ef4444' },
};

export const RouteCard: React.FC<RouteCardProps> = ({
  routes,
  selectedRouteId,
  onSelectRoute,
}) => {
  if (!routes || routes.length === 0) {
    return (
      <div className="simple-card route-comparison-card">
        <div className="card-header-simple">
          <span className="card-icon">📊</span>
          <h3 className="card-title">Route Comparison</h3>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0.5rem 0' }}>
          No candidate routes to compare. Enter valid source and destination to compute candidate routes.
        </p>
      </div>
    );
  }

  // Filter passable candidates for computing dynamic badges
  const passable = routes.filter(
    (r) => r.isPassable !== false && !r.name.toLowerCase().includes('closed')
  );
  const candidates = passable.length > 0 ? passable : routes;

  const minEta = Math.min(...candidates.map((r) => r.etaMinutes));
  const minRisk = Math.min(...candidates.map((r) => r.riskPercent));

  // Show Traffic column only if at least one route has traffic data
  const hasTrafficData = routes.some((r) => r.trafficStatus != null);

  const getStatusText = (risk: number, isClosed: boolean, isRec: boolean) => {
    if (isClosed) return 'Closed';
    if (isRec) return 'Recommended';
    if (risk <= 25) return 'Low Risk';
    if (risk <= 50) return 'Moderate';
    if (risk <= 75) return 'High Risk';
    return 'Severe';
  };

  return (
    <div className="simple-card route-comparison-card">
      <div className="card-header-simple">
        <span className="card-icon">📊</span>
        <h3 className="card-title">Route Comparison</h3>
      </div>

      <div className="simple-table-wrapper">
        <table className="simple-table">
          <thead>
            <tr>
              <th>Route</th>
              <th>ETA</th>
              <th>Distance</th>
              {hasTrafficData && <th>Traffic</th>}
              <th>Risk</th>
              <th>Reliability</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((route) => {
              const isSelected = route.id === selectedRouteId;
              const isRec = route.isRecommended;
              const isClosed =
                route.isPassable === false || route.name.toLowerCase().includes('closed');

              const isFastest = !isClosed && route.etaMinutes === minEta;
              const isSafest = !isClosed && route.riskPercent === minRisk;

              const trafficCfg = route.trafficStatus
                ? TRAFFIC_CONFIG[route.trafficStatus] ?? null
                : null;

              return (
                <tr
                  key={route.id}
                  className={`table-row ${isSelected ? 'row-active' : ''} ${
                    isRec ? 'row-rec' : ''
                  } ${isClosed ? 'row-closed' : ''}`}
                  onClick={() => onSelectRoute(route.id)}
                >
                  <td className="cell-route-code">
                    <div className="route-code-wrapper">
                      <span
                        className="route-dot-indicator"
                        style={{
                          backgroundColor: isClosed
                            ? '#dc2626'
                            : isRec
                            ? '#10b981'
                            : route.color || '#38bdf8',
                        }}
                      ></span>
                      <div>
                        <strong>{route.code}</strong>
                        <div className="corridor-subtext">{route.name}</div>
                      </div>
                    </div>
                  </td>

                  <td className="cell-eta">
                    <strong>{route.etaMinutes} min</strong>
                  </td>

                  <td className="cell-dist">
                    {route.distanceKm} km
                  </td>

                  {hasTrafficData && (
                    <td className="cell-traffic">
                      {trafficCfg ? (
                        <span
                          style={{
                            color: trafficCfg.color,
                            fontWeight: 600,
                            fontSize: '0.8rem',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {trafficCfg.icon} {route.trafficStatus}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>—</span>
                      )}
                    </td>
                  )}

                  <td className="cell-risk">
                    <span
                      className="risk-val-pill"
                      style={{
                        color: isClosed
                          ? '#ef4444'
                          : route.riskPercent > 50
                          ? '#ef4444'
                          : route.riskPercent > 25
                          ? '#f59e0b'
                          : '#10b981',
                      }}
                    >
                      {route.riskPercent}%
                    </span>
                  </td>

                  <td className="cell-rel">
                    {Math.round(route.reliabilityScore * 100)}%
                  </td>

                  <td className="cell-status">
                    <div className="status-badges-group">
                      {isClosed && (
                        <span className="badge-tag tag-closed">CLOSED</span>
                      )}
                      {isRec && !isClosed && (
                        <span className="badge-tag tag-rec">RECOMMENDED</span>
                      )}
                      {isFastest && !isClosed && (
                        <span className="badge-tag tag-fast">FASTEST</span>
                      )}
                      {isSafest && !isClosed && !isRec && (
                        <span className="badge-tag tag-safe">SAFEST</span>
                      )}
                      {!isRec && !isFastest && !isSafest && !isClosed && (
                        <span className="badge-tag tag-candidate">
                          {getStatusText(route.riskPercent, isClosed, isRec)}
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {routes.length === 1 && (
        <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          ℹ️ Only one viable direct route is currently available for this corridor.
        </div>
      )}
    </div>
  );
};

export default RouteCard;

