import React from 'react';
import { RouteItem } from '../../types/route';

interface ExplanationPanelProps {
  recommendedRoute: RouteItem;
  allRoutes?: RouteItem[];
  systemExplanation?: string[];
}

export const ExplanationPanel: React.FC<ExplanationPanelProps> = ({
  recommendedRoute,
  allRoutes = [],
  systemExplanation = [],
}) => {
  if (!recommendedRoute) {
    return (
      <div className="simple-card why-route-card">
        <div className="card-header-simple">
          <span className="card-icon">💡</span>
          <h3 className="card-title">Why this Route?</h3>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0.5rem 0' }}>
          AI route decision rationale will appear here after analyzing candidate paths.
        </p>
      </div>
    );
  }

  // Extract clean positive reasons for the recommended route
  const getCleanReasons = (): string[] => {
    if (systemExplanation && systemExplanation.length > 0) {
      const reasons: string[] = [];
      let capturing = false;

      for (const line of systemExplanation) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.toLowerCase().includes('recommended because:')) {
          capturing = true;
          continue;
        } else if (trimmed.toLowerCase().includes('not selected because:')) {
          capturing = false;
        } else if (capturing) {
          reasons.push(trimmed.replace(/^•\s*/, ''));
        }
      }

      if (reasons.length > 0) return reasons;
    }

    // Grounded fallback derived from actual route properties
    const reasons: string[] = [];
    const fastest = allRoutes.reduce(
      (prev, curr) => (curr.etaMinutes < prev.etaMinutes ? curr : prev),
      recommendedRoute
    );

    if (recommendedRoute.id === fastest.id) {
      reasons.push(`Fastest candidate route (${recommendedRoute.etaMinutes} min ETA)`);
    } else {
      const diff = recommendedRoute.etaMinutes - fastest.etaMinutes;
      reasons.push(`Only +${diff} min slower than the fastest route (${fastest.code})`);
    }

    if ((recommendedRoute.riskFactors?.traffic || 0) <= 0.35) {
      reasons.push(`Lower traffic congestion risk (${Math.round((recommendedRoute.riskFactors?.traffic || 0) * 100)}%)`);
    }

    if ((recommendedRoute.riskFactors?.incident || 0) === 0) {
      reasons.push('No confirmed incident or emergency lane disruption');
    }

    if ((recommendedRoute.riskFactors?.weather || 0) <= 0.25) {
      reasons.push('Favorable weather conditions along corridor');
    }

    if (recommendedRoute.reliabilityScore >= 0.85) {
      reasons.push(`High reliability index (${Math.round(recommendedRoute.reliabilityScore * 100)}%)`);
    }

    return reasons.length > 0 ? reasons : ['Optimal multi-criteria mission safety and speed'];
  };

  const reasons = getCleanReasons();

  return (
    <div className="simple-card why-route-card">
      <div className="card-header-simple">
        <span className="card-icon">💡</span>
        <h3 className="card-title">Why {recommendedRoute.code}?</h3>
      </div>

      <ul className="why-reasons-list">
        {reasons.map((reason, idx) => (
          <li key={idx} className="why-reason-item">
            <span className="why-check">✓</span>
            <span className="why-text">{reason}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ExplanationPanel;

