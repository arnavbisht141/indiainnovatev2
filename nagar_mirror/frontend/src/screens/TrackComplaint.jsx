import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'

// Build WebSocket URL dynamically — works in both dev and production
function buildWsUrl(complaintId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    // In dev with Vite proxy, we talk to the same host (Vite proxies /api to backend)
    return `${protocol}//${host}/api/complaints/${complaintId}/ws`
}

const STATUS_LABELS = {
    filed: { label: 'Filed', color: 'var(--warning)', pill: 'pill-filed' },
    assigned: { label: 'Assigned', color: 'var(--accent)', pill: 'pill-closed' },
    resolved_pending_citizen: { label: 'Pending Your Review', color: 'var(--success)', pill: 'pill-resolved' },
    closed: { label: 'Closed ✓', color: 'var(--success)', pill: 'pill-closed' },
    reopened: { label: 'Reopened (Disputed)', color: 'var(--danger)', pill: 'pill-reopened' },
    offline_pending: { label: 'Saved Offline', color: 'var(--warning)', pill: 'pill-filed' },
}

export default function TrackComplaint() {
    const { id } = useParams()
    const navigate = useNavigate()

    const [ticketId, setTicketId] = useState(id || '')
    const [complaint, setComplaint] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const fetchStatus = async (cid) => {
        setLoading(true); setError(''); setComplaint(null)
        try {
            const data = await api.getComplaint(cid)
            setComplaint(data)
        } catch (err) {
            setError("Complaint not found. Check the ID or try again.")
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (id) fetchStatus(id)
    }, [id])

    useEffect(() => {
        if (!complaint || complaint.status === 'offline_pending') return

        let ws
        try {
            ws = new WebSocket(buildWsUrl(complaint.id))

            ws.onopen = () => console.log('WS connected for', complaint.id)
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)
                    if (data.status) {
                        setComplaint(prev => ({ ...prev, status: data.status }))
                    }
                } catch { /* ignore parse errors */ }
            }
            ws.onerror = () => { /* silent — WS is optional enhancement */ }
        } catch { /* WebSocket not available */ }

        // Keepalive ping every 30 seconds
        const interval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping')
        }, 30000)

        return () => {
            clearInterval(interval)
            if (ws) ws.close()
        }
    }, [complaint?.id])

    const handleSearch = (e) => {
        e.preventDefault()
        if (ticketId.trim()) navigate(`/track/${ticketId.trim()}`)
    }

    const statusInfo = complaint ? (STATUS_LABELS[complaint.status] || { label: complaint.status, color: 'var(--text-secondary)', pill: '' }) : null

    return (
        <div className="page-header">
            <h1 className="page-title">Track Status</h1>

            {!id && (
                <form onSubmit={handleSearch} style={{ marginTop: '24px' }}>
                    <div className="form-group">
                        <input
                            type="text"
                            className="form-input"
                            placeholder="Enter Complaint ID..."
                            value={ticketId}
                            onChange={e => setTicketId(e.target.value)}
                            required
                        />
                    </div>
                    <button className="btn btn-primary btn-full">Search</button>

                    <div style={{ marginTop: '40px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                        Or log in via DigiLocker to see all your complaints automatically.
                    </div>
                </form>
            )}

            {loading && <div style={{ marginTop: '60px', textAlign: 'center' }}><div className="spinner"></div></div>}
            {error && (
                <div style={{ color: 'var(--danger)', marginTop: '24px', padding: '16px', background: 'rgba(248,113,113,0.08)', borderRadius: '12px', border: '1px solid rgba(248,113,113,0.2)' }}>
                    ⚠️ {error}
                </div>
            )}

            {complaint && !loading && (
                <div style={{ marginTop: '24px' }}>
                    <div className="card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                            <div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Ticket ID</div>
                                <div style={{ fontFamily: 'monospace', fontWeight: 600, fontSize: '0.85rem', color: 'var(--accent)' }}>
                                    {complaint.id.substring(0, 13)}...
                                </div>
                            </div>

                            <span className={`pill ${statusInfo?.pill}`} style={{ color: statusInfo?.color }}>
                                {statusInfo?.label}
                            </span>
                        </div>

                        <h3 style={{ fontSize: '1.1rem', marginBottom: '6px', textTransform: 'capitalize' }}>
                            {complaint.complaint_type.replace('_', ' ')}
                        </h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: '16px', lineHeight: 1.5 }}>
                            {complaint.description}
                        </p>

                        <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                            <span>📅 {new Date(complaint.filed_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                            <span className={`sev-${complaint.severity_estimate}`}>● {complaint.severity_estimate.toUpperCase()}</span>
                        </div>

                        {complaint.officer_name && (
                            <div style={{ background: 'var(--bg-elevated)', padding: '12px', borderRadius: '10px', marginBottom: '16px', display: 'flex', gap: '12px', alignItems: 'center' }}>
                                <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem' }}>👮</div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Assigned Officer</div>
                                    <div style={{ fontWeight: 600 }}>{complaint.officer_name}</div>
                                    {complaint.estimated_resolution && (
                                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Est. resolution: {complaint.estimated_resolution}</div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* TIMELINE */}
                        {complaint.timeline && complaint.timeline.length > 0 && (
                            <div style={{ marginTop: '20px' }}>
                                <h4 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '16px', letterSpacing: '0.05em' }}>Timeline</h4>
                                <div className="timeline">
                                    {complaint.timeline.map((item, i) => (
                                        <div key={i} className="timeline-item">
                                            <div className="timeline-dot"></div>
                                            <div className="timeline-event">{item.event}</div>
                                            <div className="timeline-time">{new Date(item.timestamp).toLocaleString('en-IN')} • {item.actor || 'system'}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                    </div>

                    {complaint.status === 'resolved_pending_citizen' && (
                        <div style={{ marginTop: '20px' }}>
                            <div style={{ padding: '20px', background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.25)', borderRadius: '16px', textAlign: 'center' }}>
                                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🤝</div>
                                <h3 style={{ color: 'var(--success)', marginBottom: '8px', fontSize: '1rem' }}>Officer claims this is fixed.</h3>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px' }}>
                                    Please confirm to close the ticket, or dispute if the issue persists.
                                </p>
                                <button className="btn btn-primary btn-full" onClick={() => navigate(`/dispute/${complaint.id}`)}>
                                    Review & Give Verdict
                                </button>
                            </div>
                        </div>
                    )}

                    {complaint.status === 'offline_pending' && (
                        <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.25)', borderRadius: '12px' }}>
                            <div style={{ color: 'var(--warning)', fontWeight: 600, marginBottom: '4px' }}>📶 Saved Offline</div>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                                This complaint is queued. It will be submitted automatically when your connection is restored.
                            </p>
                        </div>
                    )}

                    <button className="btn btn-ghost btn-full" style={{ marginTop: '16px' }} onClick={() => navigate('/file')}>
                        + File Another Complaint
                    </button>
                </div>
            )}
        </div>
    )
}
