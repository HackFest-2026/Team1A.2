import React, { useMemo, useState, useEffect } from 'react';
import { GeoJSON, Circle, CircleMarker, Popup, Tooltip, useMap } from 'react-leaflet';
import worldLandData from '../world_land.json';
import {
  INDIA_COASTLINE,
  SRI_LANKA_COASTLINE,
  ANDAMAN_CHAIN,
  NICOBAR_CHAIN,
  LAKSHADWEEP_ISLANDS,
  INDIAN_EEZ_BOUNDARY,
  TACTICAL_GRATICULES,
  STRATEGIC_HUBS,
  TACTICAL_PLACES,
  MARITIME_REGIONS
} from '../offlineGeoData';

export interface OfflineGeoOverlayProps {
  enabled?: boolean;
  basemapMode?: string;
  showStrategicHubs?: boolean;
  showPlaceNames?: boolean;
}

/**
 * Reusable 100% Air-Gapped Sovereign Vector Overlay for Leaflet Maps.
 * Renders Peninsular India Coastline, Sri Lanka, Island Chains,
 * 200nm Sovereign EEZ, Tactical Graticules (MGRS), Coastal Radar Rings,
 * Tactical Place Names (Littoral Cities/Ports) and Maritime Water Bodies.
 * ZERO external network calls. ZERO CDN dependencies.
 */
export const OfflineGeoOverlay: React.FC<OfflineGeoOverlayProps> = ({
  enabled = true,
  basemapMode = 'basemap',
  showStrategicHubs = true,
  showPlaceNames = true
}) => {
  const map = useMap();
  const [zoomLevel, setZoomLevel] = useState<number>(map ? map.getZoom() : 6);

  useEffect(() => {
    if (!map) return;
    const handleZoom = () => {
      setZoomLevel(map.getZoom());
    };
    map.on('zoomend', handleZoom);
    return () => {
      map.off('zoomend', handleZoom);
    };
  }, [map]);

  const tacticalGeoJsonData = useMemo<any>(() => {
    const worldFeatures = ((worldLandData as any)?.features || []).map((f: any, idx: number) => ({
      ...f,
      id: f.id || `world-land-${idx}`,
      properties: {
        ...(f.properties || {}),
        type: 'LANDMASS'
      }
    }));

    const operationalFeatures = [
      {
        type: 'Feature',
        properties: { name: 'Indian Sovereign Littoral Coastline', type: 'COASTLINE' },
        geometry: {
          type: 'LineString',
          coordinates: INDIA_COASTLINE.map(([lat, lon]) => [lon, lat])
        }
      },
      {
        type: 'Feature',
        properties: { name: 'Sri Lanka Coastline', type: 'COASTLINE' },
        geometry: {
          type: 'LineString',
          coordinates: SRI_LANKA_COASTLINE.map(([lat, lon]) => [lon, lat])
        }
      },
      {
        type: 'Feature',
        properties: { name: 'Andaman Archipelago', type: 'COASTLINE' },
        geometry: {
          type: 'LineString',
          coordinates: ANDAMAN_CHAIN.map(([lat, lon]) => [lon, lat])
        }
      },
      {
        type: 'Feature',
        properties: { name: 'Nicobar Archipelago', type: 'COASTLINE' },
        geometry: {
          type: 'LineString',
          coordinates: NICOBAR_CHAIN.map(([lat, lon]) => [lon, lat])
        }
      },
      {
        type: 'Feature',
        properties: { name: 'Lakshadweep Archipelago', type: 'COASTLINE' },
        geometry: {
          type: 'LineString',
          coordinates: LAKSHADWEEP_ISLANDS.map(([lat, lon]) => [lon, lat])
        }
      },
      {
        type: 'Feature',
        properties: { name: 'Indian Sovereign EEZ Boundary (200nm)', type: 'EEZ' },
        geometry: {
          type: 'LineString',
          coordinates: INDIAN_EEZ_BOUNDARY.map(([lat, lon]) => [lon, lat])
        }
      },
      ...TACTICAL_GRATICULES.map(g => ({
        type: 'Feature',
        properties: { name: g.name, type: 'GRATICULE' },
        geometry: {
          type: 'LineString',
          coordinates: g.points.map(([lat, lon]) => [lon, lat])
        }
      }))
    ];

    return {
      type: 'FeatureCollection',
      features: [...worldFeatures, ...operationalFeatures]
    };
  }, []);

  const visiblePlaces = useMemo(() => {
    if (!showPlaceNames) return [];
    if (zoomLevel >= 6) return TACTICAL_PLACES;
    if (zoomLevel >= 4) return TACTICAL_PLACES.filter(p => p.tier === 1);
    return TACTICAL_PLACES.filter(p => p.tier === 1 && (p.category === 'METRO_PORT' || p.category === 'NAVAL_PORT'));
  }, [showPlaceNames, zoomLevel]);

  const visibleWaterRegions = useMemo(() => {
    if (!showPlaceNames) return [];
    return MARITIME_REGIONS.filter(reg => zoomLevel >= reg.zoomMin && zoomLevel <= reg.zoomMax);
  }, [showPlaceNames, zoomLevel]);

  if (!enabled) return null;

  const tacticalGeoJsonStyle = (feature: any) => {
    const fType = feature?.properties?.type;
    if (fType === 'LANDMASS') {
      return {
        fillColor: '#122637',
        fillOpacity: 0.95,
        color: 'rgba(56, 189, 248, 0.45)',
        weight: 1.0,
        opacity: 0.8
      };
    }
    if (fType === 'COASTLINE') {
      return {
        color: '#00f0ff',
        weight: 3.0,
        opacity: 1.0
      };
    }
    if (fType === 'EEZ') {
      return {
        color: '#f59e0b',
        weight: 2.2,
        dashArray: '6 6',
        opacity: 0.95
      };
    }
    if (fType === 'GRATICULE') {
      return {
        color: 'rgba(56, 189, 248, 0.25)',
        weight: 1,
        dashArray: '3 6',
        opacity: 0.6
      };
    }
    return { color: '#00f0ff', weight: 1.5 };
  };

  return (
    <>
      <GeoJSON
        key={`geo-overlay-${basemapMode}`}
        data={tacticalGeoJsonData}
        style={tacticalGeoJsonStyle}
      />

      {/* Maritime Regional Water Body Labels (Arabian Sea, Bay of Bengal, Indian Ocean, etc.) */}
      {visibleWaterRegions.map(reg => (
        <CircleMarker
          key={reg.id}
          center={[reg.lat, reg.lon]}
          radius={0.01}
          pathOptions={{ stroke: false, fill: false }}
        >
          <Tooltip
            permanent
            direction="center"
            className="tactical-water-tooltip"
            interactive={false}
          >
            <span style={{
              letterSpacing: reg.letterSpacing || '4px',
              fontSize: reg.fontSize || '12px'
            }}>
              {reg.name}
            </span>
          </Tooltip>
        </CircleMarker>
      ))}

      {/* Strategic Naval Commands, Project Seabird & International Chokepoints */}
      {showStrategicHubs && STRATEGIC_HUBS.map(hub => {
        const isHQ = hub.type === 'COMMAND_HQ';
        return (
          <span key={hub.id}>
            <Circle
              center={[hub.lat, hub.lon]}
              radius={hub.radarRangeKm * 1000}
              pathOptions={{
                color: isHQ ? '#06b6d4' : '#64748b',
                fillColor: isHQ ? '#06b6d4' : '#64748b',
                fillOpacity: 0.04,
                weight: 1,
                dashArray: '3 5'
              }}
            />
            <CircleMarker
              center={[hub.lat, hub.lon]}
              radius={isHQ ? 6 : 4}
              pathOptions={{
                color: isHQ ? '#00f0ff' : '#94a3b8',
                fillColor: '#071622',
                fillOpacity: 1,
                weight: 2
              }}
            >
              {showPlaceNames && (
                <Tooltip
                  permanent
                  direction="top"
                  offset={[0, -8]}
                  className="tactical-hub-tooltip"
                >
                  <span>{hub.code}</span>
                </Tooltip>
              )}
              <Popup>
                <div style={{ fontSize: '11px', fontFamily: 'monospace' }}>
                  <b style={{ color: '#00f0ff' }}>{hub.name}</b>
                  <div style={{ color: '#94a3b8', fontSize: '9px' }}>
                    CALLSIGN: {hub.code} | TYPE: {hub.type}
                  </div>
                  <div style={{ color: '#f59e0b', fontSize: '9px', marginTop: '2px' }}>
                    COASTAL RADAR RANGE: {hub.radarRangeKm} KM
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          </span>
        );
      })}

      {/* Littoral Tactical Cities, Ports & Stations with Permanent Place Name Labels */}
      {visiblePlaces.map(place => (
        <CircleMarker
          key={place.id}
          center={[place.lat, place.lon]}
          radius={place.tier === 1 ? 3.5 : 2.5}
          pathOptions={{
            color: place.category === 'NAVAL_PORT' ? '#00f0ff' : place.category === 'STRATEGIC_ISLAND' ? '#38bdf8' : '#94a3b8',
            fillColor: '#071622',
            fillOpacity: 0.95,
            weight: 1.5
          }}
        >
          <Tooltip
            permanent
            direction="right"
            offset={[6, 0]}
            className="tactical-place-tooltip"
          >
            <span>{place.shortName}</span>
          </Tooltip>
          <Popup>
            <div style={{ fontSize: '11px', fontFamily: 'monospace' }}>
              <b style={{ color: '#38bdf8' }}>{place.name}</b>
              <div style={{ color: '#94a3b8', fontSize: '9px' }}>
                POS: {place.lat.toFixed(3)}°N, {place.lon.toFixed(3)}°E
              </div>
              <div style={{ color: '#a7f3d0', fontSize: '9px', marginTop: '2px' }}>
                TYPE: {place.category.replace('_', ' ')}
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  );
};

export default OfflineGeoOverlay;

