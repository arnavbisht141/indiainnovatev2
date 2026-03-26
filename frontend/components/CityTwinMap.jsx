'use client';
import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Health score → color ──────────────────────────────────────────────────────
function healthColor(score) {
  if (score >= 70) return '#22c55e';  // green  — healthy
  if (score >= 40) return '#f59e0b';  // amber  — warning
  return '#ef4444';                   // red    — critical
}

// ── Node type → icon label ────────────────────────────────────────────────────
const TYPE_ICON = {
  drain:        '🔵',
  transformer:  '⚡',
  toilet:       '🚻',
  park:         '🌿',
  water_main:   '💧',
  road:         '🛣️',
  garbage_zone: '🗑️',
  // legacy keys from old dummy data
  DrainNode:    '🔵',
  Transformer:  '⚡',
  PublicToilet: '🚻',
  ParkNode:     '🌿',
  WaterMain:    '💧',
  ParkingZone:  '🅿️',
  WastePoint:   '🗑️',
};

export default function CityTwinMap() {
  const mapContainer = useRef(null);
  const map          = useRef(null);
  const markers      = useRef([]);

  // ── State ───────────────────────────────────────────────────────────────────
  const [nodes,       setNodes]       = useState([]);
  const [cascadeIds,  setCascadeIds]  = useState([]);
  const [selected,    setSelected]    = useState(null);
  const [mapLoaded,   setMapLoaded]   = useState(false);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);

  // ── Fetch nodes from backend on mount ───────────────────────────────────────
  useEffect(() => {
    setLoading(true);
    fetch(`${API}/api/zones/connaught_place/coordinates`)
      .then(r => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      })
      .then(data => {
        setNodes(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load nodes:', err);
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // ── Fetch cascade chain when a node is clicked ───────────────────────────────
  const handleNodeClick = async (node) => {
    setSelected(node);
    setCascadeIds([]); // clear previous cascade
    try {
      const res = await fetch(`${API}/api/nodes/${node.id}/cascade?depth=3`);
      if (!res.ok) return; // silently skip if cascade not available
      const chain = await res.json();
      setCascadeIds(chain.map(n => n.id));
    } catch (e) {
      console.error('Cascade fetch failed:', e);
    }
  };

  // ── Init map ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (map.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style:     'mapbox://styles/mapbox/dark-v11',
      center:    [77.2197, 28.6328],   // CP center [lng, lat]
      zoom:      15.5,
      pitch:     55,
      bearing:   -17,
      antialias: true,
    });

    map.current.on('load', () => {
      setMapLoaded(true);
      add3DBuildings();
      addCPRings();
    });

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

    return () => {
      markers.current.forEach(m => m.remove());
      map.current?.remove();
      map.current = null;
    };
  }, []);

  // ── Render markers whenever map + nodes change ───────────────────────────────
  useEffect(() => {
    if (!mapLoaded || !map.current || nodes.length === 0) return;

    // Remove old markers
    markers.current.forEach(m => m.remove());
    markers.current = [];

    nodes.forEach(node => {
      const isCritical = node.health_score < 40;
      const isCascade  = cascadeIds.includes(node.id);
      const color      = healthColor(node.health_score);

      const el = document.createElement('div');
      el.className = 'twin-marker';
      el.style.cssText = `
        width: ${isCritical ? '22px' : '16px'};
        height: ${isCritical ? '22px' : '16px'};
        border-radius: 50%;
        background: ${color};
        border: ${isCascade ? '3px solid #f59e0b' : '2px solid rgba(255,255,255,0.3)'};
        cursor: pointer;
        box-shadow: ${isCascade
          ? `0 0 20px #f59e0b, 0 0 8px ${color}`
          : `0 0 ${isCritical ? '12px' : '6px'} ${color}`
        };
        animation: ${isCritical ? 'pulse 1.5s infinite' : 'none'};
      `;

      // API returns `lng`; old dummy data used `lon` — handle both
      const lng = node.lng ?? node.lon;
      const lat = node.lat;

      const marker = new mapboxgl.Marker({ element: el, anchor: 'center' })
        .setLngLat([lng, lat])
        .addTo(map.current);

      el.addEventListener('click', () => handleNodeClick(node));
      markers.current.push(marker);
    });
  }, [mapLoaded, nodes, cascadeIds]);

  // ── 3D buildings ─────────────────────────────────────────────────────────────
  function add3DBuildings() {
    const layers = map.current.getStyle().layers;
    const labelLayer = layers.find(l => l.type === 'symbol' && l.layout?.['text-field']);

    map.current.addLayer({
      id:     '3d-buildings',
      source: 'composite',
      'source-layer': 'building',
      filter: ['==', 'extrude', 'true'],
      type:   'fill-extrusion',
      minzoom: 14,
      paint: {
        'fill-extrusion-color':   '#1a1a2e',
        'fill-extrusion-height':  ['get', 'height'],
        'fill-extrusion-base':    ['get', 'min_height'],
        'fill-extrusion-opacity': 0.8,
      },
    }, labelLayer?.id);
  }

  // ── CP center ring ────────────────────────────────────────────────────────────
  function addCPRings() {
    map.current.addSource('cp-rings', {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          properties: {},
          geometry: { type: 'Point', coordinates: [77.2197, 28.6328] }
        }]
      }
    });

    map.current.addLayer({
      id:     'cp-center',
      type:   'circle',
      source: 'cp-rings',
      paint: {
        'circle-radius':       6,
        'circle-color':        '#6366f1',
        'circle-opacity':      0.6,
        'circle-stroke-width': 2,
        'circle-stroke-color': '#818cf8',
      }
    });
  }

  // ── Cascade heatmap ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapLoaded || !map.current) return;

    // Clean up previous heatmap
    if (map.current.getLayer('cascade-heat-layer')) {
      map.current.removeLayer('cascade-heat-layer');
    }
    if (map.current.getSource('cascade-heat')) {
      map.current.removeSource('cascade-heat');
    }

    if (cascadeIds.length === 0) return;

    const cascadeNodes = nodes.filter(n => cascadeIds.includes(n.id));
    if (cascadeNodes.length === 0) return;

    map.current.addSource('cascade-heat', {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: cascadeNodes.map(n => ({
          type: 'Feature',
          properties: { weight: (100 - n.health_score) / 100 },
          geometry: { type: 'Point', coordinates: [n.lng ?? n.lon, n.lat] }
        }))
      }
    });

    map.current.addLayer({
      id:     'cascade-heat-layer',
      type:   'heatmap',
      source: 'cascade-heat',
      paint: {
        'heatmap-weight':    ['get', 'weight'],
        'heatmap-intensity': 1.5,
        'heatmap-radius':    60,
        'heatmap-opacity':   0.5,
        'heatmap-color': [
          'interpolate', ['linear'], ['heatmap-density'],
          0,   'rgba(0,0,0,0)',
          0.3, 'rgba(245,158,11,0.3)',
          0.7, 'rgba(239,68,68,0.5)',
          1,   'rgba(239,68,68,0.8)',
        ]
      }
    }, 'cp-center');
  }, [mapLoaded, cascadeIds, nodes]);

  // ── Summary counts ────────────────────────────────────────────────────────────
  const critical = nodes.filter(n => n.health_score < 40).length;
  const warning  = nodes.filter(n => n.health_score >= 40 && n.health_score < 70).length;
  const healthy  = nodes.filter(n => n.health_score >= 70).length;

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div style={{ position: 'relative', width: '100%', height: '100vh', background: '#0f0f1a' }}>

      {/* Pulse animation */}
      <style>{`
        @keyframes pulse {
          0%   { box-shadow: 0 0 6px #ef4444, 0 0 0 0 rgba(239,68,68,0.6); }
          70%  { box-shadow: 0 0 6px #ef4444, 0 0 0 12px rgba(239,68,68,0); }
          100% { box-shadow: 0 0 6px #ef4444, 0 0 0 0 rgba(239,68,68,0); }
        }
      `}</style>

      {/* Map canvas */}
      <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

      {/* Loading overlay */}
      {loading && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(15,15,26,0.8)', color: '#818cf8', fontSize: 16,
          flexDirection: 'column', gap: 12,
        }}>
          <div style={{ fontSize: 28 }}>🏙️</div>
          Loading city twin data…
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div style={{
          position: 'absolute', top: 16, left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)',
          borderRadius: 10, padding: '10px 16px', color: '#fca5a5', fontSize: 13,
        }}>
          ⚠️ Backend unreachable — check that uvicorn is running on port 8000
        </div>
      )}

      {/* Top-left title bar */}
      <div style={{
        position: 'absolute', top: 16, left: 16,
        background: 'rgba(15,15,26,0.9)',
        border: '1px solid rgba(99,102,241,0.3)',
        borderRadius: 12, padding: '12px 16px',
        color: '#fff', backdropFilter: 'blur(10px)',
      }}>
        <div style={{ fontSize: 13, color: '#818cf8', marginBottom: 4 }}>
          NAGARMIRROR — CITY TWIN
        </div>
        <div style={{ fontSize: 18, fontWeight: 700 }}>Connaught Place</div>
        <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
          {nodes.length} nodes monitored
        </div>
      </div>

      {/* Top-right legend */}
      <div style={{
        position: 'absolute', top: 16, right: 60,
        background: 'rgba(15,15,26,0.9)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 12, padding: '12px 16px',
        color: '#fff', backdropFilter: 'blur(10px)',
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        <div style={{ fontSize: 11, color: '#818cf8', marginBottom: 2 }}>HEALTH STATUS</div>
        {[
          { label: `Critical (${critical})`, color: '#ef4444', range: '< 40' },
          { label: `Warning (${warning})`,   color: '#f59e0b', range: '40–69' },
          { label: `Healthy (${healthy})`,   color: '#22c55e', range: '≥ 70' },
        ].map(item => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
            <div style={{
              width: 10, height: 10, borderRadius: '50%',
              background: item.color, boxShadow: `0 0 6px ${item.color}`
            }} />
            <span>{item.label}</span>
            <span style={{ color: '#64748b', marginLeft: 'auto', paddingLeft: 8 }}>{item.range}</span>
          </div>
        ))}
      </div>

      {/* Node detail panel */}
      {selected && (
        <div style={{
          position: 'absolute', bottom: 24, left: 16,
          background: 'rgba(15,15,26,0.95)',
          border: `1px solid ${healthColor(selected.health_score)}44`,
          borderRadius: 16, padding: '16px 20px',
          color: '#fff', backdropFilter: 'blur(12px)',
          minWidth: 260, maxWidth: 320,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
            <div>
              <div style={{ fontSize: 11, color: '#818cf8' }}>
                {TYPE_ICON[selected.type] || '📍'} {(selected.type || '').toUpperCase()}
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, marginTop: 4 }}>{selected.name}</div>
            </div>
            <button
              onClick={() => { setSelected(null); setCascadeIds([]); }}
              style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 18 }}
            >×</button>
          </div>

          {/* Health bar */}
          <div style={{ marginTop: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
              <span>Health Score</span>
              <span style={{ color: healthColor(selected.health_score), fontWeight: 700 }}>
                {selected.health_score}/100
              </span>
            </div>
            <div style={{ background: '#1e1e2e', borderRadius: 4, height: 8, overflow: 'hidden' }}>
              <div style={{
                width: `${selected.health_score}%`,
                height: '100%',
                background: healthColor(selected.health_score),
                borderRadius: 4,
                transition: 'width 0.5s ease',
                boxShadow: `0 0 8px ${healthColor(selected.health_score)}`,
              }} />
            </div>
          </div>

          <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[
              { label: 'Zone',       value: selected.zone_type || selected.zone || '—' },
              { label: 'Status',     value: selected.status || (selected.health_score < 40 ? 'critical' : selected.health_score < 70 ? 'warning' : 'healthy') },
              { label: 'Complaints', value: selected.active_complaints ?? selected.complaint_count ?? 0 },
              { label: 'Node ID',    value: (selected.id || '').slice(0, 12) + '…' },
            ].map(item => (
              <div key={item.label} style={{
                background: 'rgba(255,255,255,0.04)',
                borderRadius: 8, padding: '8px 10px',
              }}>
                <div style={{ fontSize: 10, color: '#64748b' }}>{item.label}</div>
                <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{item.value}</div>
              </div>
            ))}
          </div>

          {selected.health_score < 40 && (
            <div style={{
              marginTop: 12, padding: '8px 12px',
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 8, fontSize: 12, color: '#fca5a5',
            }}>
              ⚠️ Critical — cascade risk detected. Inspection recommended.
            </div>
          )}
        </div>
      )}

      {/* Cascade badge */}
      {cascadeIds.length > 0 && (
        <div style={{
          position: 'absolute', bottom: 24, right: 16,
          background: 'rgba(245,158,11,0.15)',
          border: '1px solid rgba(245,158,11,0.5)',
          borderRadius: 12, padding: '10px 14px',
          color: '#fbbf24', fontSize: 13,
          backdropFilter: 'blur(10px)',
        }}>
          🔥 Cascade active — {cascadeIds.length} nodes at risk
        </div>
      )}
    </div>
  );
}