import React from 'react';
import {
  RouteItem,
  DataStatusSummary,
  SimulatedRouteComparisonDTO,
  MissionProfileDTO,
  DataFeedStatus,
} from '../../types/route';

interface PresentationModeProps {
  recommendedRoute: RouteItem;
  selectedRoute: RouteItem;
  allRoutes: RouteItem[];
  systemExplanation: string[];
  dataStatus: DataStatusSummary;
  simComparison: SimulatedRouteComparisonDTO[];
  isSimulated: boolean;
  recommendationFlipped: boolean;
  optimizationProfile?: MissionProfileDTO;
  vehicleType: string;
  priority: string;
  activeDemoScenarioName: string | null;
  onExit: () => void;
  onLaunchTour?: () => void;
}

const riskColor = (pct: number): string => {
  if (pct < 25) return '#10b981';
  if (pct < 50) return '#f59e0b';
  if (pct < 75) return '#f97316';
  return '#ef4444';
};

const riskLabel = (pct: number): string => {
  if (pct < 25) return 'LOW';
  if (pct < 50) return 'MODERATE';
  if (pct < 75) return 'HIGH';
  return 'SEVERE';
};

const confidenceColor = (conf: string): string => {
  switch (conf.toLowerCase()) {
    case 'high': return '#10b981';
    case 'moderate': return '#f59e0b';
    default: return '#ef4444';
  }
};

const feedStatusLabel = (feed: DataFeedStatus): string => {
  if (feed.status === 'UNAVAILABLE') return 'UNAVAILABLE';
  if (feed.freshness === 'FRESH') return 'LIVE';
  if (feed.freshness === 'RECENT') return 'RECENT';
  if (feed.freshness === 'STALE') return 'STALE';
  return feed.status;
};

const feedStatusColor = (label: string): string => {
  if (label === 'LIVE' || label === 'RECENT') return '#10b981';
  if (label === 'STALE') return '#f97316';
  if (label === 'UNAVAILABLE') return '#94a3b8';
  return '#f59e0b';
};

const computeRouteLabels = (routes: RouteItem[]): Record<string, string[]> => {
  const labels: Record<string, string[]> = {};
  if (!routes.length) return labels;
  const passable = routes.filter((r) => r.isPassable !== false);
  if (!passable.length) return labels;
  const fastest = passable.reduce((a, b) => (a.etaMinutes < b.etaMinutes ? a : b));
  const safest  = passable.reduce((a, b) => (a.riskPercent < b.riskPercent ? a : b));
  const mostRel = passable.reduce((a, b) => (a.reliabilityScore > b.reliabilityScore ? a : b));
  const recommended = routes.find((r) => r.isRecommended);
  routes.forEach((r) => {
    labels[r.id] = [];
    if (recommended && r.id === recommended.id) labels[r.id].push('RECOMMENDED');
    if (r.id === fastest.id) labels[r.id].push('FASTEST');
    if (r.id === safest.id) labels[r.id].push('SAFEST');
    if (r.id === mostRel.id) labels[r.id].push('MOST RELIABLE');
  });
  return labels;
};

const PIPELINE_STEPS = [
  { icon: 'A1', label: 'Routes Generated', sub: 'OSRM + OpenStreetMap vector graph' },
  { icon: 'A2', label: 'Traffic + Weather + Incidents', sub: 'Open-Meteo, Municipal sensors, CAD dispatch' },
  { icon: 'A3', label: 'Risk Analysis', sub: '4-factor weighted composite score' },
  { icon: 'A4', label: 'Delay Prediction', sub: 'ML regressor with rule-based fallback' },
  { icon: 'A5', label: 'Route Optimization', sub: 'Mission profile weights (Speed / Safety / Reliability)' },
  { icon: 'A6', label: 'Recommendation', sub: 'Lowest composite score with grounded explainability' },
];


const PmHeroCard: React.FC<{ route: RouteItem }> = ({ route }) => {
  const rc = riskColor(route.riskPercent);
  const rl = riskLabel(route.riskPercent);
  const passable = route.isPassable !== false;
  return (
    <div className={`pm-hero-card ${route.isRecommended ? 'pm-hero-best' : 'pm-hero-alt'} ${!passable ? 'pm-hero-closed' : ''}`}>
      {!passable && <div className="pm-closed-banner">ROUTE CLOSED / IMPASSABLE</div>}
      <div className="pm-hero-top">
        <div className="pm-hero-badge">{route.isRecommended ? 'RECOMMENDED' : 'VIEWING'}</div>
        <div className="pm-hero-code">{route.code}</div>
        <div className="pm-hero-name">{route.name}</div>
      </div>
      <div className="pm-hero-stats">
        <div className="pm-stat-box">
          <span className="pm-stat-val">{route.etaMinutes}<span className="pm-stat-unit"> min</span></span>
          <span className="pm-stat-lbl">ETA</span>
        </div>
        <div className="pm-stat-box">
          <span className="pm-stat-val">{route.distanceKm.toFixed(1)}<span className="pm-stat-unit"> km</span></span>
          <span className="pm-stat-lbl">Distance</span>
        </div>
        <div className="pm-stat-box">
          <span className="pm-stat-val" style={{ color: rc }}>{route.riskPercent}<span className="pm-stat-unit">%</span></span>
          <span className="pm-stat-lbl">Risk</span>
        </div>
        <div className="pm-stat-box">
          <span className="pm-stat-val">{route.confidenceScore}<span className="pm-stat-unit">%</span></span>
          <span className="pm-stat-lbl">Confidence</span>
        </div>
        {route.predictedDelayMinutes !== undefined && (
          <div className="pm-stat-box">
            <span className="pm-stat-val" style={{ color: route.predictedDelayMinutes > 3 ? '#f97316' : '#10b981' }}>
              +{route.predictedDelayMinutes.toFixed(1)}<span className="pm-stat-unit"> min</span>
            </span>
            <span className="pm-stat-lbl">Predicted Delay</span>
          </div>
        )}
      </div>
      <div className="pm-hero-risk-badge" style={{ background: rc + '22', borderColor: rc, color: rc }}>
        {rl} RISK
        {route.delayPredictionSource && (
          <span className="pm-source-tag">{route.delayPredictionSource === 'ml' ? 'ML' : 'Rule-Based'}</span>
        )}
      </div>
    </div>
  );
};

const LABEL_COLORS: Record<string, string> = {
  RECOMMENDED: '#10b981', FASTEST: '#38bdf8', SAFEST: '#a78bfa', 'MOST RELIABLE': '#fbbf24',
};

const PmRouteCompare: React.FC<{ routes: RouteItem[] }> = ({ routes }) => {
  const labels = computeRouteLabels(routes);
  return (
    <div className="pm-section">
      <div className="pm-section-title">Route Comparison</div>
      <div className="pm-route-table">
        <div className="pm-table-head">
          <span>Route</span><span>ETA</span><span>Risk</span><span>Score</span><span>Delay</span><span>Labels</span>
        </div>
        {routes.map((r) => {
          const rc = riskColor(r.riskPercent);
          const passable = r.isPassable !== false;
          const routeLabels = labels[r.id] || [];
          return (
            <div key={r.id} className={`pm-table-row ${r.isRecommended ? 'pm-row-rec' : ''} ${!passable ? 'pm-row-closed' : ''}`}>
              <span className="pm-col-code">
                <span className="pm-route-dot" style={{ background: r.color }} />
                {r.code}
                {!passable && <span className="pm-closed-tag">CLOSED</span>}
              </span>
              <span className="pm-col-eta">{r.etaMinutes} min</span>
              <span className="pm-col-risk" style={{ color: rc }}>{r.riskPercent}%</span>
              <span className="pm-col-score">{r.overallScore?.toFixed(2) ?? '-'}</span>
              <span className="pm-col-delay">{r.predictedDelayMinutes !== undefined ? '+' + r.predictedDelayMinutes.toFixed(1) + 'm' : '-'}</span>
              <span className="pm-col-labels">
                {routeLabels.map((lbl) => (
                  <span key={lbl} className="pm-route-label" style={{ borderColor: LABEL_COLORS[lbl] ?? '#64748b', color: LABEL_COLORS[lbl] ?? '#64748b' }}>
                    {lbl}
                  </span>
                ))}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const PmRiskBreakdown: React.FC<{ route: RouteItem }> = ({ route }) => {
  const factors = [
    { key: 'Traffic', val: route.riskFactors.traffic },
    { key: 'Weather', val: route.riskFactors.weather },
    { key: 'Incident', val: route.riskFactors.incident },
    { key: 'Road', val: route.riskFactors.road },
  ];
  return (
    <div className="pm-section">
      <div className="pm-section-title">Risk Breakdown — {route.code}</div>
      <div className="pm-risk-bars">
        {factors.map(({ key, val }) => {
          const pct = Math.round(val * 100);
          const col = riskColor(pct);
          return (
            <div key={key} className="pm-risk-row">
              <span className="pm-risk-lbl">{key}</span>
              <div className="pm-risk-track">
                <div className="pm-risk-fill" style={{ width: pct + '%', background: col }} />
              </div>
              <span className="pm-risk-pct" style={{ color: col }}>{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const PmExplanation: React.FC<{ route: RouteItem; systemExplanation: string[] }> = ({ route, systemExplanation }) => {
  const bullets: string[] = [];
  if (systemExplanation.length > 0) {
    let inRec = false;
    for (const line of systemExplanation) {
      const t = line.trim();
      if (!t) continue;
      if (t.toLowerCase().includes('recommended because:')) { inRec = true; continue; }
      if (t.toLowerCase().includes('not selected because:')) { inRec = false; }
      if (inRec && t.startsWith('-')) bullets.push(t.slice(1).trim());
      if (bullets.length >= 4) break;
    }
  }
  if (bullets.length === 0) route.explanationPoints.slice(0, 4).forEach((p) => bullets.push(p));
  return (
    <div className="pm-section pm-section-explain">
      <div className="pm-section-title">Why {route.code} Was Selected</div>
      <ul className="pm-explain-list">
        {bullets.map((b, i) => (
          <li key={i} className="pm-explain-item"><span className="pm-explain-check">✓</span>{b}</li>
        ))}
        {bullets.length === 0 && <li className="pm-explain-item pm-explain-empty">Run analysis to generate explanation.</li>}
      </ul>
    </div>
  );
};

const PmDecisionPipeline: React.FC<{ optimizationProfile?: MissionProfileDTO; vehicleType: string; priority: string }> = ({ optimizationProfile, vehicleType, priority }) => {
  const profileLabel = optimizationProfile?.profile_label ?? vehicleType + ' / ' + priority;
  const ICONS = ['🛰️', '🌦️', '⚠️', '🤖', '📊', '✅'];
  return (
    <div className="pm-section pm-section-pipeline">
      <div className="pm-section-title">How SmartRoute Decided</div>
      <div className="pm-pipeline-profile">Profile: <strong>{profileLabel}</strong></div>
      <div className="pm-pipeline-flow">
        {PIPELINE_STEPS.map((step, idx) => (
          <React.Fragment key={idx}>
            <div className="pm-pipeline-step">
              <span className="pm-pipeline-icon">{ICONS[idx]}</span>
              <div className="pm-pipeline-text">
                <span className="pm-pipeline-label">{step.label}</span>
                <span className="pm-pipeline-sub">{step.sub}</span>
              </div>
            </div>
            {idx < PIPELINE_STEPS.length - 1 && <div className="pm-pipeline-arrow">↓</div>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

const PmDataStatus: React.FC<{ dataStatus: DataStatusSummary }> = ({ dataStatus }) => {
  const confCol = confidenceColor(dataStatus.confidence);
  return (
    <div className="pm-section pm-section-data">
      <div className="pm-section-title">Data Pipeline Status</div>
      <div className="pm-feed-badges">
        {dataStatus.feeds.map((feed) => {
          const sl = feedStatusLabel(feed);
          const col = feedStatusColor(sl);
          return (
            <div key={feed.name} className="pm-feed-badge">
              <span className="pm-feed-name">{feed.name}</span>
              <span className="pm-feed-status" style={{ color: col, borderColor: col }}>{sl}</span>
              <span className="pm-feed-age">{feed.ageFormatted}</span>
            </div>
          );
        })}
      </div>
      <div className="pm-confidence-row">
        <span className="pm-conf-label">Overall Confidence</span>
        <span className="pm-conf-val" style={{ color: confCol }}>{dataStatus.confidence} ({dataStatus.confidencePercent}%)</span>
      </div>
    </div>
  );
};

const PmSimComparison: React.FC<{ comparison: SimulatedRouteComparisonDTO[]; recommendationFlipped: boolean }> = ({ comparison, recommendationFlipped }) => {
  if (!comparison.length) return null;
  return (
    <div className="pm-section pm-section-sim">
      <div className="pm-section-title">
        Live vs What-If Simulation
        {recommendationFlipped && <span className="pm-flipped-badge">RECOMMENDATION FLIPPED</span>}
      </div>
      <div className="pm-sim-table">
        <div className="pm-sim-head"><span>Route</span><span>Live ETA</span><span>Sim ETA</span><span>Live Risk</span><span>Sim Risk</span><span>Passable</span></div>
        {comparison.map((c) => {
          const etaDelta = c.simulated_eta_minutes - c.current_eta_minutes;
          const riskDelta = c.simulated_risk_percent - c.current_risk_percent;
          return (
            <div key={c.id} className={`pm-sim-row ${c.is_simulated_recommended ? 'pm-sim-rec' : ''}`}>
              <span className="pm-col-code">{c.code}{c.is_simulated_recommended && <span className="pm-sim-rec-tag">REC</span>}</span>
              <span>{c.current_eta_minutes} min</span>
              <span className={etaDelta > 0 ? 'pm-delta-worse' : 'pm-delta-better'}>{c.simulated_eta_minutes} min {etaDelta !== 0 && '(' + (etaDelta > 0 ? '+' : '') + etaDelta.toFixed(0) + ')'}</span>
              <span>{c.current_risk_percent}%</span>
              <span className={riskDelta > 0 ? 'pm-delta-worse' : 'pm-delta-better'}>{c.simulated_risk_percent}% {riskDelta !== 0 && '(' + (riskDelta > 0 ? '+' : '') + riskDelta.toFixed(0) + ')'}</span>
              <span style={{ color: c.is_passable ? '#10b981' : '#ef4444' }}>{c.is_passable ? 'Open' : 'Closed'}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const PresentationMode: React.FC<PresentationModeProps> = ({
  recommendedRoute,
  allRoutes,
  systemExplanation,
  dataStatus,
  simComparison,
  isSimulated,
  recommendationFlipped,
  optimizationProfile,
  vehicleType,
  priority,
  activeDemoScenarioName,
  onExit,
  onLaunchTour,
}) => (
  <div className="pm-overlay">
    <header className="pm-header">
      <div className="pm-header-brand">
        <span className="pm-header-icon">⚡</span>
        <div>
          <span className="pm-header-title">SMARTROUTE AI</span>
          <span className="pm-header-sub">Emergency Route Intelligence · Presentation Mode</span>
        </div>
      </div>
      <div className="pm-header-center">
        <div className="pm-mission-pill">
          <span className="pm-mission-dot" />
          <span>Mission: <strong>{vehicleType}</strong> · Priority: <strong>{priority}</strong></span>
        </div>
        {activeDemoScenarioName && <div className="pm-demo-pill">DEMO: {activeDemoScenarioName}</div>}
      </div>
      <div className="pm-header-actions">
        {onLaunchTour && <button type="button" className="pm-tour-btn" onClick={onLaunchTour}>Run Full Demo</button>}
        <button type="button" className="pm-exit-btn" onClick={onExit}>Exit Presentation</button>
      </div>
    </header>

    <div className="pm-body">
      <div className="pm-col-left">
        <PmHeroCard route={recommendedRoute} />
        <PmRouteCompare routes={allRoutes} />
        {isSimulated && <PmSimComparison comparison={simComparison} recommendationFlipped={recommendationFlipped} />}
      </div>
      <div className="pm-col-right">
        <PmRiskBreakdown route={recommendedRoute} />
        <PmExplanation route={recommendedRoute} systemExplanation={systemExplanation} />
        <PmDecisionPipeline optimizationProfile={optimizationProfile} vehicleType={vehicleType} priority={priority} />
        <PmDataStatus dataStatus={dataStatus} />
      </div>
    </div>
  </div>
);

export default PresentationMode;
