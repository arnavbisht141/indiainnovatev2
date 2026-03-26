import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Home() {
    const navigate = useNavigate()
    const [score, setScore] = useState(null)

    useEffect(() => {
        // Quickly fetch Ward trust score just for the summary
        api.getTrustScore('connaught_place').then(setScore).catch(console.error)
    }, [])

    return (
        <div className="page-header" style={{ display: 'flex', flexDirection: 'column', gap: '32px', marginTop: '20px' }}>

            <div>
                <h1 className="page-title">Connaught Place Ward</h1>
                <p className="page-subtitle" style={{ fontSize: '1.05rem', marginTop: '8px' }}>
                    {score ? (
                        score.overall_score >= 80 ? <span style={{ color: 'var(--success)' }}>Operational & Trusted.</span> :
                            score.overall_score >= 60 ? <span style={{ color: 'var(--warning)' }}>Needs Attention.</span> :
                                <span style={{ color: 'var(--danger)' }}>Critical Infrastructure Failures.</span>
                    ) : 'Loading status...'}
                </p>
            </div>

            <div className="card" style={{ textAlign: 'center', padding: '36px 20px', background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.4) 0%, rgba(56,189,248,0.08) 100%)', border: '1px solid var(--glass-border-hover)' }}>
                <h2 style={{ fontSize: '1.3rem', marginBottom: '8px' }}>See a problem?</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
                    Report broken infrastructure in CP — drains, roads, power, water — instantly.
                </p>

                <button
                    className="btn btn-primary btn-full btn-lg"
                    onClick={() => navigate('/file')}
                >
                    <span style={{ fontSize: '1.3rem' }}>🎙️</span> File Complaint
                </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <button className="card btn" onClick={() => navigate('/track')} style={{ flexDirection: 'column', padding: '24px 16px', gap: '12px' }}>
                    <span style={{ fontSize: '1.8rem' }}>📍</span>
                    <span>Track Status</span>
                </button>

                <button className="card btn" onClick={() => navigate('/dashboard/trust')} style={{ flexDirection: 'column', padding: '24px 16px', gap: '12px' }}>
                    <span style={{ fontSize: '1.8rem' }}>📊</span>
                    <span>Public Trust</span>
                </button>

                <button className="card btn" onClick={() => navigate('/dashboard/equity')} style={{ flexDirection: 'column', padding: '24px 16px', gap: '12px' }}>
                    <span style={{ fontSize: '1.8rem' }}>🗺️</span>
                    <span>Equity Map</span>
                </button>

                <button className="card btn" onClick={() => navigate('/dashboard/narratives')} style={{ flexDirection: 'column', padding: '24px 16px', gap: '12px' }}>
                    <span style={{ fontSize: '1.8rem' }}>📖</span>
                    <span>Narratives</span>
                </button>
            </div>

        </div>
    )
}
