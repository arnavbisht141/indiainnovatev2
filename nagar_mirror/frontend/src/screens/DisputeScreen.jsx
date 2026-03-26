import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function DisputeScreen() {
    const { id } = useParams()
    const navigate = useNavigate()

    const [complaint, setComplaint] = useState(null)
    const [loading, setLoading] = useState(true)
    const [submitting, setSubmitting] = useState(false)
    const [notes, setNotes] = useState('')

    useEffect(() => {
        api.getComplaint(id).then(data => {
            setComplaint(data)
            setLoading(false)
        }).catch(() => {
            alert("Error loading complaint")
            navigate('/track')
        })
    }, [id, navigate])

    const handleVerdict = async (verdict) => {
        setSubmitting(true)
        try {
            await api.disputeResolution(id, verdict, notes)
            alert(verdict === 'fixed' ? 'Thank you! Ticket Closed.' : 'Disputed! Ticket Re-opened & Escalated.')
            navigate(`/track/${id}`)
        } catch (err) {
            alert("Failed to submit verdict")
            setSubmitting(false)
        }
    }

    if (loading) return <div className="page-header"><div className="spinner"></div></div>

    return (
        <div className="page-header">
            <h1 className="page-title">Officer resolution</h1>
            <p className="page-subtitle">Ticket: {id.split('-').pop()}</p>

            <div className="card" style={{ marginTop: '24px' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
                    <div style={{ fontSize: '2rem' }}>🤝</div>
                    <div>
                        <h2 style={{ fontSize: '1.1rem' }}>Officer {complaint.officer_name || 'Assigned'}</h2>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>marked this fixed 12 mins ago.</p>
                    </div>
                </div>

                <div style={{ background: 'var(--bg-elevated)', padding: '16px', borderRadius: '8px', marginBottom: '24px' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>YOUR COMPLAINT</div>
                    <p style={{ fontWeight: 500 }}>{complaint.description}</p>
                </div>

                <h3 style={{ fontSize: '1rem', marginBottom: '16px', textAlign: 'center' }}>Is the issue resolved?</h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <button
                        className="btn btn-success btn-lg"
                        onClick={() => handleVerdict('fixed')}
                        disabled={submitting}
                    >
                        ✅ Yes, it is fixed
                    </button>

                    <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem', margin: '8px 0' }}>OR</div>

                    <div className="form-group">
                        <input
                            className="form-input"
                            placeholder="Why is it still broken? (Optional notes for escalation)"
                            value={notes}
                            onChange={e => setNotes(e.target.value)}
                        />
                    </div>
                    <button
                        className="btn btn-danger btn-lg"
                        onClick={() => handleVerdict('still_broken')}
                        disabled={submitting}
                    >
                        ❌ No, it is still broken
                    </button>
                </div>

                <p style={{ marginTop: '24px', fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                    Your response is securely logged to the Public Trust Ledger and cannot be altered by officers.
                </p>
            </div>
        </div>
    )
}
