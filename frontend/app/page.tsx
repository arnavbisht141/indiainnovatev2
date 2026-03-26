'use client';
import dynamic from 'next/dynamic';

// Mapbox requires browser APIs — must disable SSR
const CityTwinMap = dynamic(
  () => import('../components/CityTwinMap'),
  { ssr: false, loading: () => (
    <div style={{
      width: '100vw', height: '100vh',
      background: '#0f0f1a',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: '#818cf8', fontSize: 16, flexDirection: 'column', gap: 12,
    }}>
      <div style={{ fontSize: 28 }}>🏙️</div>
      Loading NagarMirror...
    </div>
  )}
);

export default function Home() {
  return <CityTwinMap />;
}