import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts'
import { api } from '../api'

export default function WardTrustScore() {
    const navigate = useNavigate()
    const [score, setScore] = useState(null)
    const [trend, setTrend] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        Promise.all([
            api.getTrustScore('connaught_place'),
            api.getTrustTrend('connaught_place')
        ]).then(([s, t]) => {
            setScore(s)
            setTrend([...t].reverse()) // API returns newest first, reverse for chart left-to-right
            setLoading(false)
        }).catch(console.error)
    }, [])

    if (loading) return <div className="page-header"><div className="spinner"></div></div>

    const radarData = score ? [
        { subject: 'Resolution Authenticity', A: score.resolution_authenticity, fullMark: 100 },
        { subject: 'Proactive Rate', A: score.proactive_rate, fullMark: 100 },
        { subject: 'Recurrence Prevention', A: score.recurrence_prevention, fullMark: 100 },
        { subject: 'Response Equity', A: score.response_equity, fullMark: 100 },
        { subject: 'Moral Alert', A: score.moral_alert_response, fullMark: 100 },
    ] : []

    return (
        <div className="page-header" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 className="page-title">Trust Ledger</h1>
                    <p className="page-subtitle">Connaught Place Ward</p>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div className="health-value" style={{ color: score?.overall_score > 70 ? 'var(--success)' : 'var(--warning)', fontSize: '2.5rem' }}>
                        {score?.overall_score}
                    </div>
                    <div className="health-label">System Trust</div>
                </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
                <button className="btn btn-primary" style={{ flex: 1 }} disabled>⚖️ Ledger</button>
                <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => navigate('/dashboard/equity')}>🗺️ Equity</button>
                <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => navigate('/dashboard/narratives')}>📖 Stories</button>
            </div>

            {/* ── Radar Chart ── */}
            <div className="card">
                <h3 style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginBottom: '8px', textAlign: 'center' }}>5-Axis Performance</h3>
                <div style={{ width: '100%', height: 300 }}>
                    <ResponsiveContainer>
                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                            <PolarGrid stroke="var(--border)" />
                            <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                            <Radar name="Score" dataKey="A" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.4} />
                        </RadarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* ── Trend Line ── */}
            <div className="card">
                <h3 style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginBottom: '16px', textAlign: 'center' }}>12-Week Trust Trend</h3>
                <div style={{ width: '100%', height: 200, marginLeft: '-15px' }}>
                    <ResponsiveContainer>
                        <LineChart data={trend}>
                            <XAxis dataKey="week" stroke="var(--border)" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickFormatter={t => t.slice(5, 10)} />
                            <YAxis domain={[0, 100]} stroke="var(--border)" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                            <Tooltip
                                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '8px', color: '#fff' }}
                                itemStyle={{ color: 'var(--accent)' }}
                            />
                            <Line type="monotone" dataKey="overall_score" stroke="var(--success)" strokeWidth={3} dot={{ fill: 'var(--bg-base)', strokeWidth: 2 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* ── Definitions ── */}
            <div style={{ padding: '0 8px', display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
                {[
                    { t: 'Resolution Authenticity', d: 'Percentage of officer resolutions actively confirmed by citizens.' },
                    { t: 'Proactive Rate', d: 'Issues fixed by municipal workers before a citizen complained.' },
                    { t: 'Recurrence Prevention', d: 'Measurement of how rarely a "fixed" issue breaks again within 30 days.' },
                    { t: 'Response Equity', d: 'Variance in response times between high-income and low-income blocks.' },
                    { t: 'Moral Alert Response', d: 'Speed of fixing "critical" life-threatening failures.' }
                ].map(item => (
                    <div key={item.t}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{item.t}</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{item.d}</div>
                    </div>
                ))}
            </div>

        </div>
    )
}
