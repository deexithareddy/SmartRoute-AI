import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, Tooltip, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { RouteItem, IncidentDTO } from '../../types/route';
import { LOCATION_ORIGIN, LOCATION_DESTINATION, MAP_CENTER } from '../../mock/mockRoutes';

// Helper to determine route stroke color based on risk level and recommended status
export const getRouteColor = (route: RouteItem): string => {
  if (route.isPassable === false || route.name.toLowerCase().includes('closed')) {
    return '#dc2626'; // Red for closed
  }
  if (route.isRecommended) {
    return '#10b981'; // Green for recommended
  }
  // Alternate distinct color based on route code or color property
  return route.color || '#38bdf8';
};

// Map Bounds Auto-fitter
const MapBoundsAdjuster: React.FC<{
  routes: RouteItem[];
  originCoords?: [number, number];
  destCoords?: [number, number];
}> = ({ routes, originCoords, destCoords }) => {
  const map = useMap();

  useEffect(() => {
    if (routes && routes.length > 0) {
      const points: [number, number][] = [];
      if (originCoords) points.push(originCoords);
      if (destCoords) points.push(destCoords);

      for (const r of routes) {
        for (const c of r.coordinates) {
          points.push(c);
        }
      }

      if (points.length > 0) {
        const bounds = L.latLngBounds(points.map((p) => [p[0], p[1]]));
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
      }
    } else {
      // Default view on Hyderabad metropolitan region
      map.setView(MAP_CENTER, 11.5);
    }
  }, [routes, originCoords, destCoords, map]);

  return null;
};

// Custom Leaflet DivIcon Generators
const createCustomIcon = (label: string, emoji: string, bgClass: string) => {
  return L.divIcon({
    className: 'custom-map-marker',
    html: `
      <div class="map-marker-pin ${bgClass}">
        <span class="marker-icon">${emoji}</span>
        <div class="marker-title">${label}</div>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 34],
    popupAnchor: [0, -34],
  });
};

const createIncidentIcon = (eventType: string) => {
  return L.divIcon({
    className: 'custom-map-marker',
    html: `
      <div class="map-marker-pin marker-incident">
        <span class="marker-icon">⚠️</span>
        <div class="marker-title">${eventType || 'INCIDENT'}</div>
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30],
  });
};

const originIcon = createCustomIcon('Origin', '🏥', 'marker-origin');
const destIcon = createCustomIcon('Destination', '🎯', 'marker-dest');

interface MapProps {
  routes: RouteItem[];
  selectedRouteId: string;
  onSelectRoute: (id: string) => void;
  originCoords?: [number, number];
  destinationCoords?: [number, number];
  originName?: string;
  destinationName?: string;
  incidents?: IncidentDTO[];
}

export const Map: React.FC<MapProps> = ({
  routes,
  selectedRouteId,
  onSelectRoute,
  originCoords = MAP_CENTER,
  destinationCoords,
  originName = LOCATION_ORIGIN.name,
  destinationName = LOCATION_DESTINATION.name,
  incidents = [],
}) => {
  const activeRoute = routes.find((r) => r.id === selectedRouteId) || routes[0];

  return (
    <div className="simple-card map-card">
      <div className="map-card-header">
        <div className="map-header-left">
          <span className="card-icon">🗺️</span>
          <h3 className="card-title">Hyderabad Emergency Route Map</h3>
        </div>

        {/* Route Quick Selector Pills */}
        <div className="map-route-pills">
          {routes.map((r) => {
            const isSelected = r.id === selectedRouteId;
            const isRec = r.isRecommended;
            return (
              <button
                key={r.id}
                type="button"
                className={`route-pill ${isSelected ? 'pill-active' : ''} ${
                  isRec ? 'pill-rec' : ''
                }`}
                onClick={() => onSelectRoute(r.id)}
              >
                <span
                  className="pill-color-dot"
                  style={{ backgroundColor: getRouteColor(r) }}
                ></span>
                <span>{r.code}</span>
                {isRec && <span className="rec-star">⭐</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="map-container-frame">
        <MapContainer
          center={MAP_CENTER}
          zoom={11.5}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%', minHeight: '440px' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          />

          <MapBoundsAdjuster
            routes={routes}
            originCoords={originCoords}
            destCoords={destinationCoords}
          />

          {/* Origin Marker */}
          {originCoords && (
            <Marker position={originCoords} icon={originIcon}>
              <Popup>
                <div className="popup-body">
                  <strong>🏥 Source: {originName}</strong>
                </div>
              </Popup>
            </Marker>
          )}

          {/* Destination Marker */}
          {destinationCoords && (
            <Marker position={destinationCoords} icon={destIcon}>
              <Popup>
                <div className="popup-body">
                  <strong>🎯 Destination: {destinationName}</strong>
                </div>
              </Popup>
            </Marker>
          )}

          {/* Incidents (if any) */}
          {incidents &&
            incidents.map((inc, idx) => (
              <Marker
                key={`inc-${inc.incident_id || idx}`}
                position={[inc.lat, inc.lng]}
                icon={createIncidentIcon(inc.event_type)}
              >
                <Popup>
                  <div className="popup-body">
                    <strong>⚠️ {inc.headline}</strong>
                    <p>{inc.location_name}</p>
                  </div>
                </Popup>
              </Marker>
            ))}

          {/* Route Polylines */}
          {routes.map((route) => {
            const isSelected = route.id === selectedRouteId;
            const isRec = route.isRecommended;
            const color = getRouteColor(route);

            return (
              <React.Fragment key={route.id}>
                {/* Halo for recommended or selected route */}
                {(isRec || isSelected) && (
                  <Polyline
                    positions={route.coordinates}
                    pathOptions={{
                      color: isRec ? '#10b981' : color,
                      weight: isRec ? 12 : 10,
                      opacity: isRec ? 0.35 : 0.2,
                      lineCap: 'round',
                      lineJoin: 'round',
                    }}
                  />
                )}

                {/* Main Polyline */}
                <Polyline
                  positions={route.coordinates}
                  pathOptions={{
                    color: color,
                    weight: isRec ? 6 : isSelected ? 5 : 4,
                    opacity: isSelected ? 1.0 : 0.75,
                    lineCap: 'round',
                    lineJoin: 'round',
                  }}
                  eventHandlers={{
                    click: () => onSelectRoute(route.id),
                  }}
                >
                  <Tooltip sticky direction="top">
                    <div>
                      <strong>{route.code}: {route.name}</strong>
                      <div>⏱️ {route.etaMinutes} min | 📏 {route.distanceKm} km | ⚠️ Risk: {route.riskPercent}%</div>
                      {isRec && <div>⭐ RECOMMENDED</div>}
                    </div>
                  </Tooltip>
                </Polyline>
              </React.Fragment>
            );
          })}
        </MapContainer>
      </div>

      {/* Clean Bottom Summary Bar */}
      {activeRoute && (
        <div className="map-footer-summary">
          <span className="footer-route-name">
            <strong>{activeRoute.code}:</strong> {activeRoute.name}
          </span>
          <span className="footer-metrics">
            ⏱️ {activeRoute.etaMinutes} min &bull; 📏 {activeRoute.distanceKm} km &bull; ⚠️ {activeRoute.riskPercent}% Risk
          </span>
        </div>
      )}
    </div>
  );
};

export default Map;
