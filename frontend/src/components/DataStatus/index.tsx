import React from 'react';
import { DataStatusSummary } from '../../types/route';

interface DataStatusProps {
  statusData: DataStatusSummary;
}

export const DataStatus: React.FC<DataStatusProps> = ({ statusData }) => {
  const getFeedStatus = (feedName: string) => {
    const feed = statusData.feeds?.find((f) =>
      f.name.toLowerCase().includes(feedName.toLowerCase())
    );
    if (!feed) return { isLive: true, label: 'Live' };
    const isAvail = feed.status !== 'UNAVAILABLE';
    return {
      isLive: isAvail,
      label: isAvail ? 'Live' : 'Unavailable',
    };
  };

  const traffic = getFeedStatus('traffic');
  const weather = getFeedStatus('weather');
  const incidents = getFeedStatus('news') || getFeedStatus('cad') || getFeedStatus('incident');
  const routing = getFeedStatus('maps') || getFeedStatus('routing') || getFeedStatus('geoapify');

  const confLabel = statusData.confidence?.toUpperCase() || 'HIGH';
  const confBadgeClass =
    confLabel === 'HIGH'
      ? 'conf-high'
      : confLabel === 'MODERATE'
      ? 'conf-mod'
      : 'conf-low';

  return (
    <div className="simple-card data-status-card">
      <div className="card-header-simple">
        <span className="card-icon">📡</span>
        <h3 className="card-title">Data Confidence</h3>
      </div>

      <div className="data-status-grid">
        <div className="status-item">
          <span className="status-name">Traffic</span>
          <span className={`status-pill ${traffic.isLive ? 'pill-live' : 'pill-unavail'}`}>
            <span className="status-dot"></span>
            {traffic.label}
          </span>
        </div>

        <div className="status-item">
          <span className="status-name">Weather</span>
          <span className={`status-pill ${weather.isLive ? 'pill-live' : 'pill-unavail'}`}>
            <span className="status-dot"></span>
            {weather.label}
          </span>
        </div>

        <div className="status-item">
          <span className="status-name">Incidents</span>
          <span className={`status-pill ${incidents.isLive ? 'pill-live' : 'pill-unavail'}`}>
            <span className="status-dot"></span>
            {incidents.label}
          </span>
        </div>

        <div className="status-item">
          <span className="status-name">Routing</span>
          <span className={`status-pill ${routing.isLive ? 'pill-live' : 'pill-unavail'}`}>
            <span className="status-dot"></span>
            {routing.label}
          </span>
        </div>
      </div>

      <div className="confidence-summary-row">
        <span className="conf-label-text">Overall Confidence:</span>
        <span className={`conf-summary-badge ${confBadgeClass}`}>
          {confLabel}
        </span>
      </div>
    </div>
  );
};

export default DataStatus;

