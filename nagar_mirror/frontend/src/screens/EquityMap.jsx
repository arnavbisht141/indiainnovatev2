import { useNavigate } from 'react-router-dom'

export default function EquityMap() {
    const navigate = useNavigate()

    return (
        <div className="page-header" style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '24px 20px 0' }}>
            <div style={{ marginBottom: '16px' }}>
                <h1 className="page-title">Digital Twin Native</h1>
                <p className="page-subtitle">Interactive Canvas Mapping — Connaught Place</p>
            </div>

            <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
                <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => navigate('/dashboard/trust')}>⚖️ Ledger</button>
                <button className="btn btn-primary" style={{ flex: 1 }} disabled>🗺️ Equity</button>
                <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => navigate('/dashboard/narratives')}>📖 Stories</button>
            </div>

            <div style={{
                flex: 1,
                borderRadius: 'var(--radius-lg)',
                overflow: 'hidden',
                border: '1px solid var(--glass-border)',
                position: 'relative'
            }}>
                <iframe
                    src="/cp_digital_twin.html"
                    style={{ width: '100%', height: '100%', border: 'none', background: 'transparent' }}
                    title="Connaught Place Digital Twin Engine"
                />
            </div>
        </div>
    )
}
