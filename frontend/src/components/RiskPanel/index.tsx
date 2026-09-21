import React from 'react';
import { RouteItem } from '../../types/route';

interface RiskPanelProps {
  recommendedRoute: RouteItem;
}

export const RiskPanel: React.FC<RiskPanelProps> = ({ recommendedRoute }) => {
  if (!recommendedRoute) {
    return (
      <div className="simple-card recommended-hero-card">
        <div className="rec-header-row">
          <div className="rec-title-group">
            <span className="card-icon">⚡</span>
            <h2 className="rec-main-title">Recommended Route</h2>
          </div>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '1rem 0' }}>
          No live route recommendation active. Enter valid locations and click &ldquo;ANALYZE ROUTE&rdquo;.
        </p>
      </div>
    );
  }

  const getRiskBadgeClass = (riskPercent: number) => {
    if (riskPercent <= 25) return 'badge-risk-low';
    if (riskPercent <= 50) return 'badge-risk-mod';
    if (riskPercent <= 75) return 'badge-risk-high';
    return 'badge-risk-severe';
  };

  const getRiskBadgeLabel = (riskPercent: number) => {
    if (riskPercent <= 25) return 'LOW';
    if (riskPercent <= 50) return 'MODERATE';
    if (riskPercent <= 75) return 'HIGH';
    return 'SEVERE';
  };

  const riskLabel = getRiskBadgeLabel(recommendedRoute.riskPercent);
  const badgeClass = getRiskBadgeClass(recommendedRoute.riskPercent);
  const isDemo = recommendedRoute.data_source === 'demo';

  return (
    <div className="simple-card recommended-hero-card">
      <div className="rec-header-row">
        <div className="rec-title-group">
          <span className="rec-check-icon">✓</span>
          <h2 className="rec-main-title">
            {recommendedRoute.code} &mdash; RECOMMENDED
          </h2>
          {isDemo ? (
            <span className="badge-tag tag-demo" style={{ background: '#3b82f6', color: '#fff', fontSize: '0.65rem' }}>
              DEMO DATA
            </span>
          ) : (
            <span className="badge-tag tag-live" style={{ background: '#0284c7', color: '#fff', fontSize: '0.65rem' }}>
              LIVE GEOAPIFY
            </span>
          )}
        </div>
        <span className={`risk-badge ${badgeClass}`}>
          {riskLabel} RISK
        </span>
      </div>

      <div className="rec-corridor-name">
        {recommendedRoute.name}
      </div>

      <div className="rec-metrics-grid">
        <div className="metric-cell">
          <span className="metric-cell-label">ETA</span>
          <span className="metric-cell-val val-eta">{recommendedRoute.etaMinutes} min</span>
        </div>

        <div className="metric-cell">
          <span className="metric-cell-label">Distance</span>
          <span className="metric-cell-val">{recommendedRoute.distanceKm} km</span>
        </div>

        <div className="metric-cell">
          <span className="metric-cell-label">Risk</span>
          <span className="metric-cell-val val-risk">
            {recommendedRoute.riskPercent}%
          </span>
        </div>

        <div className="metric-cell">
          <span className="metric-cell-label">Reliability</span>
          <span className="metric-cell-val">
            {Math.round(recommendedRoute.reliabilityScore * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
};

export default RiskPanel;

