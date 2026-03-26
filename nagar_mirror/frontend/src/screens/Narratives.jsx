import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Narratives() {
    const navigate = useNavigate()
    const [narratives, setNarratives] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api.getNarratives('connaught_place').then(data => {
            setNarratives(data)
            setLoading(false)
        }).catch(console.error)
    }, [])

    if (loading) return <div className="page-header"><div className="spinner"></div></div>

    return (
        <div className="page-header" style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '24px 20px 0' }}>

            <div style={{ marginBottom: '16px' }}>
                <h1 className="page-title">Suffering Narratives</h1>
                <p className="page-subtitle">Top 5 Unresolved Structural Failures</p>
            </div>

            <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
                <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => navigate('/dashboard/trust')}>⚖️ Ledger</button>
                <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => navigate('/dashboard/equity')}>🗺️ Equity</button>
                <button className="btn btn-primary" style={{ flex: 1 }} disabled>📖 Stories</button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', paddingBottom: '100px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

                <div style={{ background: 'rgba(248,113,113,0.1)', borderLeft: '4px solid var(--danger)', padding: '16px', borderRadius: '0 8px 8px 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    <strong style={{ color: 'var(--danger)' }}>Verified by the system.</strong> These are the highest-severity failures that have remained open the longest in Karol Bagh. No officer names. No blame. Just facts.
                </div>

                {narratives.length === 0 ? (
                    <div className="card" style={{ textAlign: 'center', color: 'var(--success)', padding: '40px 20px' }}>
                        🎉 No critical unresolved failures in the ward!
                    </div>
                ) : (
                    narratives.map((node, i) => (
                        <div key={node.id} className="card" style={{ position: 'relative', overflow: 'hidden' }}>
                            <div style={{ position: 'absolute', top: 0, left: 0, bottom: 0, width: '4px', background: 'var(--danger)' }}></div>

                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                <span className="pill pill-reopened">#{i + 1} Severity</span>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                                    OPEN {node.days_open} DAYS
                                </span>
                            </div>

                            <p style={{ fontSize: '1rem', lineHeight: 1.5, color: 'var(--text-primary)', marginTop: '12px' }}>
                                Citizens report a critical failure regarding the <strong>{node.complaint_type.replace('_', ' ')}</strong> infrastructure.
                                The specific verified issue is: <em>"{node.description}"</em>.
                                This severe hazard has been neglected for <strong>{node.days_open} consecutive days</strong> despite being logged in the public ledger.
                            </p>
                        </div>
                    ))
                )}

            </div>
        </div>
    )
}
