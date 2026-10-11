import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Circle,
  Popup,
  Polyline,
  Tooltip,
  useMap
} from 'react-leaflet';
import L from 'leaflet';
import { Compass, Target, ChevronRight, Anchor, Navigation, Shield, Radar, Map as MapIcon } from 'lucide-react';
import { OfflineGeoOverlay } from './OfflineGeoOverlay';
import { INDIA_COASTLINE } from '../offlineGeoData';

export interface MissionWaypoint {
  id: string;
  step: string;
  title: string;
  name: string;
  lat: number;
  lon: number;
  isIntercept: boolean;
  latLon: string;
  metrics: string;
  badgeText: string;
  badgeColor: string;
  badgeBg: string;
}

export const MISSION_WAYPOINTS: MissionWaypoint[] = [
  {
    id: 'wp-01',
    step: '01',
    title: 'STATION ORIGIN: Mumbai Naval Anchorage',
    name: 'Mumbai Naval Anchorage',
    lat: 18.9100,
    lon: 72.8400,
    isIntercept: false,
    latLon: 'Lat: 18.9100°N, Lon: 72.8400°E',
    metrics: 'Speed: 28 kts · Departure: 00:00',
    badgeText: 'DEP 00:00',
    badgeColor: '#819ba8',
    badgeBg: 'rgba(129, 155, 168, 0.15)'
  },
  {
    id: 'wp-02',
    step: '02',
    title: 'INTERCEPT 1: Dark Vessel SAR-001',
    name: 'Dark Vessel SAR-001',
    lat: 18.8920,
    lon: 72.5850,
    isIntercept: true,
    latLon: 'Lat: 18.8920°N, Lon: 72.5850°E',
    metrics: 'Range: 16.8 NM · Bearing: 254° · ETA +36 min',
    badgeText: 'THREAT 95',
    badgeColor: '#ff4d4d',
    badgeBg: 'rgba(255, 77, 77, 0.15)'
  },
  {
    id: 'wp-03',
    step: '03',
    title: 'INTERCEPT 2: Bombay High Breach SAR-002',
    name: 'Bombay High Breach SAR-002',
    lat: 19.4120,
    lon: 71.2840,
    isIntercept: true,
    latLon: 'Lat: 19.4120°N, Lon: 71.2840°E',
    metrics: 'Range: 82.4 NM · Bearing: 298° · High-speed contact',
    badgeText: 'THREAT 90',
    badgeColor: '#ff4d4d',
    badgeBg: 'rgba(255, 77, 77, 0.15)'
  },
  {
    id: 'wp-04',
    step: '04',
    title: 'PATROL SECTOR: INS Kadamba Buffer',
    name: 'INS Kadamba Buffer',
    lat: 14.7650,
    lon: 74.0240,
    isIntercept: true,
    latLon: 'Lat: 14.7650°N, Lon: 74.0240°E',
    metrics: 'Range: 260.0 NM · Southern Maritime EEZ Reconnaissance',
    badgeText: 'THREAT 88',
    badgeColor: '#eab308',
    badgeBg: 'rgba(234, 179, 8, 0.15)'
  }
];

interface MapControllerProps {
  panTarget: { lat: number; lon: number; timestamp: number } | null;
  flyTarget: { lat: number; lon: number; zoom: number; timestamp: number } | null;
  routePoints: [number, number][];
}

function MissionMapController({ panTarget, flyTarget, routePoints }: MapControllerProps) {
  const map = useMap();
  const initialFitDone = useRef(false);

  // Fit route bounds ONCE on initial mount only, preserving user manual zoom
  useEffect(() => {
    if (!initialFitDone.current && routePoints.length > 0) {
      initialFitDone.current = true;
      const allLats = routePoints.map(p => p[0]);
      const minLat = Math.min(...allLats);
      const maxLat = Math.max(...allLats);
      const relevantCoast = INDIA_COASTLINE.filter(([lat]) => lat >= minLat - 1.5 && lat <= maxLat + 1.5);
      const ptsToFit = [...routePoints, ...relevantCoast];
      const bounds = L.latLngBounds(ptsToFit.map(([lat, lon]) => [lat, lon]));
      map.fitBounds(bounds, { padding: [35, 35], maxZoom: 8 });
    }
  }, [map, routePoints]);

  // Handle pan when user selects a row
  useEffect(() => {
    if (panTarget && panTarget.lat != null && panTarget.lon != null) {
      map.panTo([panTarget.lat, panTarget.lon], { animate: true, duration: 0.8 });
    }
  }, [panTarget, map]);

  // Handle flyTo when mission is dispatched
  useEffect(() => {
    if (flyTarget && flyTarget.lat != null && flyTarget.lon != null) {
      map.flyTo([flyTarget.lat, flyTarget.lon], flyTarget.zoom, {
        duration: 1.5,
        easeLinearity: 0.25
      });
    }
  }, [flyTarget, map]);

  return null;
}

export interface MissionPlannerProps {
  opticalItems: any[];
  sarDetections: any[];
  armyFeeds: any[];
  zones: any[];
  fusedTracks?: any[];
  setToast: (msg: string) => void;
}

export const MissionPlanner: React.FC<MissionPlannerProps> = ({
  opticalItems,
  sarDetections,
  armyFeeds,
  zones,
  fusedTracks = [],
  setToast
}) => {
  type BasemapMode = 'satellite' | 'dark' | 'terrain';
  const [basemapMode, setBasemapMode] = useState<BasemapMode>('satellite');
  const [codename, setCodename] = useState<string>('OPERATION SAGAR KAVACH - INTERCEPT BRAVO');

  // SELECTABLE MISSIONS: default to the first intercept (wp-02: INTERCEPT 1)
  const [selectedWaypointId, setSelectedWaypointId] = useState<string | null>('wp-02');
  const [pulsingWaypointId, setPulsingWaypointId] = useState<string | null>(null);

  const [panTarget, setPanTarget] = useState<{ lat: number; lon: number; timestamp: number } | null>(null);
  const [flyTarget, setFlyTarget] = useState<{ lat: number; lon: number; zoom: number; timestamp: number } | null>(null);

  const markerRefs = useRef<Record<string, L.CircleMarker | null>>({});

  const selectedWaypoint = useMemo(() => {
    return MISSION_WAYPOINTS.find(w => w.id === selectedWaypointId) || null;
  }, [selectedWaypointId]);

  const routePoints: [number, number][] = useMemo(() => {
    return MISSION_WAYPOINTS.map(w => [w.lat, w.lon]);
  }, []);

  const BASEMAP_TILES: Record<string, { url: string; attr: string; maxZoom: number }> = {
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attr: '&copy; Esri World Imagery &mdash; Whole Earth Satellite Surveillance',
      maxZoom: 19
    },
    dark: {
      url: '/api/tiles/dark/{z}/{x}/{y}.png',
      attr: 'Project Rakshak 2.0 Dark Tactical (Synthetic) — Local Offline Service',
      maxZoom: 16
    },
    terrain: {
      url: '/api/tiles/terrain/{z}/{x}/{y}.png',
      attr: 'Project Rakshak 2.0 Offline Terrain (Synthetic) — synthetic, not real elevation',
      maxZoom: 19
    }
  };

  const handleSelectWaypoint = (wp: MissionWaypoint) => {
    setSelectedWaypointId(wp.id);
    setPanTarget({ lat: wp.lat, lon: wp.lon, timestamp: Date.now() });
  };

  const handleDispatch = () => {
    if (!selectedWaypoint) return;

    // Trigger pulse on the dispatched waypoint marker
    setPulsingWaypointId(selectedWaypoint.id);

    // Fly to the selected intercept: zoom 8.5, duration 1.5
    setFlyTarget({
      lat: selectedWaypoint.lat,
      lon: selectedWaypoint.lon,
      zoom: 8.5,
      timestamp: Date.now()
    });

    // Open its popup upon arrival
    setTimeout(() => {
      const marker = markerRefs.current[selectedWaypoint.id];
      if (marker) {
        marker.openPopup();
      }
    }, 1500);

    // Toast notification per requirement
    setToast(`Dispatched: ${selectedWaypoint.name}`);
  };

  return (
    <div className="mission-grid">
      <section className="panel mission-map">
        <div className="panel-head">
          <div>
            <div className="panel-title"><Compass size={16} /> Intercept & Patrol Route Vector</div>
            <small>Optimized shortest-path waypoints linking high-priority SAR dark vessels and optical contacts</small>
          </div>
        </div>

        <div className="map-wrap" style={{ height: '560px', position: 'relative' }}>
          {/* Basemap Switcher Toolbar */}
          <div style={{
            position: 'absolute',
            top: '12px',
            right: '58px',
            zIndex: 500,
            display: 'flex',
            gap: '6px'
          }}>
            <button
              onClick={() => setBasemapMode('satellite')}
              style={{
                background: basemapMode === 'satellite' ? 'rgba(6, 182, 212, 0.35)' : 'rgba(7, 18, 29, 0.85)',
                border: `1px solid ${basemapMode === 'satellite' ? '#00f0ff' : '#1e384b'}`,
                color: basemapMode === 'satellite' ? '#00f0ff' : '#728d9c',
                padding: '5px 10px',
                fontSize: '10px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontFamily: 'monospace',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '5px'
              }}
              title="Whole Earth Satellite Surveillance Imagery"
            >
              <Radar size={13} /> 🌐 WHOLE EARTH SATELLITE
            </button>
            <button
              onClick={() => setBasemapMode('dark')}
              style={{
                background: basemapMode === 'dark' ? 'rgba(6, 182, 212, 0.35)' : 'rgba(7, 18, 29, 0.85)',
                border: `1px solid ${basemapMode === 'dark' ? '#00f0ff' : '#1e384b'}`,
                color: basemapMode === 'dark' ? '#00f0ff' : '#728d9c',
                padding: '5px 10px',
                fontSize: '10px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontFamily: 'monospace',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '5px'
              }}
              title="Tactical Dark Gray Whole Earth Map (C4ISR Style)"
            >
              <Shield size={13} /> 🛡️ TACTICAL DARK C4ISR
            </button>
            <button
              onClick={() => setBasemapMode('terrain')}
              style={{
                background: basemapMode === 'terrain' ? 'rgba(6, 182, 212, 0.35)' : 'rgba(7, 18, 29, 0.85)',
                border: `1px solid ${basemapMode === 'terrain' ? '#00f0ff' : '#1e384b'}`,
                color: basemapMode === 'terrain' ? '#00f0ff' : '#728d9c',
                padding: '5px 10px',
                fontSize: '10px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontFamily: 'monospace',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '5px'
              }}
              title="Global Terrain & Bathymetry (Offline Synthetic)"
            >
              <MapIcon size={13} /> 🗺️ GLOBAL TERRAIN
            </button>
          </div>

          {/* MAP ZOOM: Enabled zoomControl (+/- buttons), scrollWheelZoom (mouse wheel), doubleClickZoom, touchZoom (pinch) */}
          <MapContainer
            center={[18.892, 72.585]}
            zoom={7}
            minZoom={2}
            maxZoom={19}
            zoomControl={true}
            scrollWheelZoom={true}
            doubleClickZoom={true}
            touchZoom={true}
            className="map"
            style={{ height: '560px', width: '100%' }}
          >
            <MissionMapController
              panTarget={panTarget}
              flyTarget={flyTarget}
              routePoints={routePoints}
            />

            <TileLayer
              key={basemapMode}
              attribution={BASEMAP_TILES[basemapMode].attr}
              url={BASEMAP_TILES[basemapMode].url}
              maxZoom={BASEMAP_TILES[basemapMode].maxZoom}
            />

            {/* Coastline and EEZ Overlay */}
            <OfflineGeoOverlay
              enabled={true}
              basemapMode={basemapMode}
              showPlaceNames={false}
            />

            {/* Mission Route Vector Polyline */}
            <Polyline
              positions={routePoints}
              pathOptions={{ color: '#06b6d4', weight: 3, dashArray: '6 8' }}
            />

            {/* Restricted Geofencing Zones */}
            {zones.map(z => (
              <Circle
                key={z.id}
                center={[z.lat, z.lon]}
                radius={z.radius_km * 1000}
                pathOptions={{
                  color: z.zone_type?.includes('EXCLUSION') ? '#ff4d4d' : '#f59e0b',
                  fillColor: z.zone_type?.includes('EXCLUSION') ? '#ff4d4d' : '#f59e0b',
                  fillOpacity: 0.12,
                  weight: 2,
                  dashArray: '4 4'
                }}
              />
            ))}

            {/* Waypoint Markers */}
            {MISSION_WAYPOINTS.map(wp => {
              const isSelected = selectedWaypointId === wp.id;
              const isPulsing = pulsingWaypointId === wp.id;

              return (
                <React.Fragment key={wp.id}>
                  {/* Pulsing Aura Circle for Selected/Dispatched Waypoint */}
                  {(isSelected || isPulsing) && (
                    <Circle
                      center={[wp.lat, wp.lon]}
                      radius={isPulsing ? 18000 : 9000}
                      pathOptions={{
                        color: wp.isIntercept ? '#ff4d4d' : '#00f0ff',
                        fillColor: wp.isIntercept ? '#ff4d4d' : '#00f0ff',
                        fillOpacity: isPulsing ? 0.35 : 0.18,
                        weight: 2,
                        dashArray: isPulsing ? '3 3' : '4 6'
                      }}
                    />
                  )}

                  <CircleMarker
                    ref={el => { markerRefs.current[wp.id] = el; }}
                    center={[wp.lat, wp.lon]}
                    radius={isSelected ? 9 : 6}
                    pathOptions={{
                      color: isSelected ? '#00f0ff' : wp.badgeColor,
                      fillColor: isSelected ? (wp.isIntercept ? '#ff4d4d' : '#00f0ff') : '#071622',
                      fillOpacity: 1,
                      weight: isSelected ? 3.5 : 2
                    }}
                    eventHandlers={{
                      click: () => handleSelectWaypoint(wp)
                    }}
                  >
                    <Tooltip permanent direction="top" offset={[0, -10]} className="tactical-hub-tooltip">
                      <span>{wp.step}: {wp.name}</span>
                    </Tooltip>
                    <Popup>
                      <div style={{ fontSize: '11px', fontFamily: 'monospace' }}>
                        <b style={{ color: isSelected ? '#00f0ff' : '#38bdf8' }}>{wp.title}</b>
                        <div style={{ color: '#94a3b8', fontSize: '9px', marginTop: '3px' }}>
                          {wp.latLon}
                        </div>
                        <div style={{ color: '#fbbf24', fontSize: '9px', marginTop: '2px' }}>
                          {wp.metrics}
                        </div>
                        <div style={{ color: wp.badgeColor, fontSize: '9px', fontWeight: 700, marginTop: '2px' }}>
                          STATUS: {wp.badgeText}
                        </div>
                      </div>
                    </Popup>
                  </CircleMarker>
                </React.Fragment>
              );
            })}
          </MapContainer>

          <div className="map-legend">
            <span style={{ color: '#38bdf8', fontWeight: 600 }}>
              <i className="dot" style={{ background: '#38bdf8' }} /> {basemapMode === 'satellite' ? 'Whole Earth High-Res Satellite' : basemapMode === 'dark' ? 'Tactical Dark C4ISR' : 'Offline terrain (synthetic)'}
            </span>
            <span><i className="dot" style={{ background: '#00f0ff' }} /> Planned Intercept Path</span>
            <span><i className="dot" style={{ background: '#ff4d4d' }} /> Selected Intercept Target</span>
            <span><i className="dot" style={{ background: '#eab308' }} /> Patrol Perimeter</span>
            <small>4 sequential mission waypoints</small>
          </div>
        </div>
      </section>

      {/* Mission Execution Sequence Panel */}
      <section className="panel mission-side">
        <div className="panel-head">
          <div>
            <div className="panel-title"><Target size={16} /> Mission Execution Sequence</div>
            <small>Tactical dispatch recommendations</small>
          </div>
        </div>

        <div style={{ padding: '15px' }}>
          <label className="field-label">
            MISSION CODENAME
            <input
              value={codename}
              onChange={e => setCodename(e.target.value)}
            />
          </label>

          <div className="mission-summary">
            <b>4</b>
            <span>Critical Intercept Waypoints</span>
          </div>

          <div className="waypoints" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {MISSION_WAYPOINTS.map(wp => {
              const isSelected = selectedWaypointId === wp.id;

              return (
                <div
                  key={wp.id}
                  onClick={() => handleSelectWaypoint(wp)}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '26px 1fr auto',
                    gap: '10px',
                    padding: '10px 12px',
                    borderBottom: '1px solid #1c3039',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    background: isSelected ? 'rgba(6, 182, 212, 0.16)' : 'rgba(7, 18, 29, 0.35)',
                    border: isSelected ? '1px solid #00f0ff' : '1px solid transparent',
                    boxShadow: isSelected ? '0 0 12px rgba(0, 240, 255, 0.25)' : 'none',
                    transition: 'all 0.18s ease'
                  }}
                  title={`Click to select and focus on ${wp.name}`}
                >
                  <span style={{ color: wp.badgeColor, fontWeight: 700, paddingTop: '2px', fontSize: '11px' }}>
                    {wp.step}
                  </span>

                  {/* LAYOUT BUG FIX: Title, Lat/Lon, and operational details on separate lines with small gap */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    <b style={{
                      color: isSelected ? '#00f0ff' : wp.isIntercept ? '#ff857f' : '#e2edf2',
                      fontSize: '11px',
                      letterSpacing: '0.2px'
                    }}>
                      {wp.title}
                    </b>
                    <div style={{ color: '#7994a3', fontSize: '9.5px', fontFamily: 'monospace' }}>
                      {wp.latLon}
                    </div>
                    <div style={{ color: '#9bb1ba', fontSize: '9px' }}>
                      {wp.metrics}
                    </div>
                  </div>

                  {/* Threat Badge Aligned Right */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-end', paddingTop: '2px' }}>
                    <span style={{
                      background: wp.badgeBg,
                      color: wp.badgeColor,
                      border: `1px solid ${wp.badgeColor}40`,
                      borderRadius: '4px',
                      padding: '2px 6px',
                      fontSize: '9px',
                      fontWeight: 700,
                      letterSpacing: '0.5px',
                      whiteSpace: 'nowrap'
                    }}>
                      {wp.badgeText}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* DISPATCH FLY-TO BUTTON */}
          <button
            className="button primary full-button"
            style={{
              marginTop: '16px',
              cursor: selectedWaypoint ? 'pointer' : 'not-allowed',
              opacity: selectedWaypoint ? 1 : 0.55
            }}
            disabled={!selectedWaypoint}
            onClick={handleDispatch}
          >
            {selectedWaypoint ? 'Dispatch Intercept Mission' : 'Select a mission'} <ChevronRight size={15} />
          </button>
        </div>
      </section>
    </div>
  );
};
