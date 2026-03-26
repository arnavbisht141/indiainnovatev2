import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const SYSTEM_PROMPT = `
You are Nagar Mirror. Extract complaint details from the citizen's voice transcript and return a pure JSON object.
Rules:
1. complaint_type Must be one of: drain, road, transformer, water_main, toilet, park, garbage_zone
2. severity_estimate Must be: low, medium, high, or critical
3. description: A clear 1-sentence summary
Return ONLY valid JSON (no markdown block, no extra text).
Example: {"complaint_type": "water_main", "severity_estimate": "high", "description": "Water pipe burst flooding the street"}
`

export default function FileComplaint() {
    const navigate = useNavigate()
    const [mode, setMode] = useState('voice') // 'voice', 'text', 'confirm'

    // Voice State
    const [isRecording, setIsRecording] = useState(false)
    const [transcript, setTranscript] = useState('')
    const [isExtracting, setIsExtracting] = useState(false)
    const [offlineToast, setOfflineToast] = useState(false)

    // Form State
    const [form, setForm] = useState({
        complaint_type: 'road',
        description: '',
        severity_estimate: 'medium',
        lat: null,
        lng: null
    })
    const [locating, setLocating] = useState(false)

    // Web Speech API refs
    const recognitionRef = useRef(null)
    const finalTranscriptRef = useRef('')

    useEffect(() => {
        // Get GPS upfront
        setLocating(true)
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                setForm(f => ({ ...f, lat: pos.coords.latitude, lng: pos.coords.longitude }))
                setLocating(false)
            },
            () => {
                // Fallback to Connaught Place center if GPS denied
                setForm(f => ({ ...f, lat: 28.6315, lng: 77.2167 }))
                setLocating(false)
            }
        )

        // Setup speech recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
        if (SpeechRecognition) {
            const recognition = new SpeechRecognition()
            recognition.continuous = true
            recognition.interimResults = true
            recognition.lang = 'hi-IN' // Hindi + English support

            recognition.onresult = (event) => {
                let interimText = ''
                let finalAddition = ''

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    const result = event.results[i]
                    if (result.isFinal) {
                        finalAddition += result[0].transcript + ' '
                    } else {
                        interimText += result[0].transcript
                    }
                }

                if (finalAddition) {
                    finalTranscriptRef.current += finalAddition
                }
                // Show final accumulated + current interim
                setTranscript(finalTranscriptRef.current + interimText)
            }

            recognition.onerror = (e) => {
                console.error('Speech error', e)
                setIsRecording(false)
            }

            recognitionRef.current = recognition
        }
    }, [])

    const toggleRecording = async () => {
        if (!recognitionRef.current) {
            alert("Voice input not supported in this browser. Switching to text mode.")
            setMode('text')
            return
        }

        if (isRecording) {
            recognitionRef.current.stop()
            setIsRecording(false)
            // Use the accumulated final transcript for extraction
            const fullTranscript = finalTranscriptRef.current.trim() || transcript.trim()
            await extractWithGemini(fullTranscript)
        } else {
            // Reset for new recording
            finalTranscriptRef.current = ''
            setTranscript('')
            recognitionRef.current.start()
            setIsRecording(true)
        }
    }

    const extractWithGemini = async (text) => {
        if (!text.trim()) { setMode('text'); return }
        setIsExtracting(true)

        const apiKey = import.meta.env.VITE_GEMINI_API_KEY
        if (!apiKey || apiKey === 'your_gemini_api_key_here') {
            console.warn("No Gemini key found. Auto-filling description from transcript.")
            setForm(f => ({ ...f, description: text.trim() }))
            setIsExtracting(false)
            setMode('confirm')
            return
        }

        try {
            const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contents: [{ parts: [{ text }] }],
                    systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
                    generationConfig: { responseMimeType: "application/json" }
                })
            })
            const data = await res.json()
            const rawText = data.candidates[0].content.parts[0].text
            const parsed = JSON.parse(rawText)

            setForm(f => ({
                ...f,
                complaint_type: parsed.complaint_type || 'road',
                severity_estimate: parsed.severity_estimate || 'medium',
                description: parsed.description || text.trim()
            }))
            setMode('confirm')
        } catch (err) {
            console.error("Gemini Extraction failed:", err)
            setForm(f => ({ ...f, description: text.trim() }))
            setMode('confirm')
        } finally {
            setIsExtracting(false)
        }
    }

    const handleSubmit = async (e) => {
        e?.preventDefault()
        try {
            const res = await api.fileComplaint({
                ...form,
                source: mode === 'confirm' ? 'voice' : 'text'
            })
            if (res.status === 'offline_pending') {
                setOfflineToast(true)
                setTimeout(() => setOfflineToast(false), 4000)
                navigate(`/track/${res.id}`)
            } else {
                navigate(res.tracking_url)
            }
        } catch (err) {
            alert("Failed to submit complaint. " + (err.message || 'Network error.'))
        }
    }

    return (
        <div className="page-header">
            <h1 className="page-title">File Complaint</h1>

            {offlineToast && (
                <div className="toast">
                    📶 Saved offline. Will sync when you're back online.
                </div>
            )}

            {/* ── MODE: VOICE ── */}
            {mode === 'voice' && (
                <div style={{ textAlign: 'center', marginTop: '60px' }}>
                    <button
                        className={`mic-btn ${isRecording ? 'recording' : ''}`}
                        onClick={toggleRecording}
                        disabled={isExtracting}
                    >
                        🎙️
                    </button>

                    <div style={{ marginTop: '40px', minHeight: '80px', color: 'var(--text-secondary)' }}>
                        {isExtracting ? (
                            <><div className="spinner" style={{ marginBottom: '16px' }}></div> AI extracting details...</>
                        ) : isRecording ? (
                            <em style={{ color: 'var(--danger)' }}>🔴 Listening... Tap mic to stop & extract</em>
                        ) : (
                            <p>Tap the mic and describe the problem in Hindi or English.<br />
                                (e.g., "Rajiv Chowk ke paas drain bhar gaya hai" or "Drain overflowing near Rajiv Chowk.")</p>
                        )}
                        {transcript && (
                            <div style={{
                                marginTop: '20px', padding: '16px', background: 'rgba(30, 41, 59, 0.4)',
                                backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
                                borderRadius: '16px', border: '1px solid var(--glass-border)',
                                fontSize: '0.9rem', color: 'var(--text-primary)', fontStyle: 'italic',
                                lineHeight: 1.6, textAlign: 'left', maxHeight: '160px', overflowY: 'auto'
                            }}>
                                "{transcript}"
                            </div>
                        )}
                    </div>

                    <div style={{ marginTop: '60px' }}>
                        <button className="btn btn-ghost" onClick={() => setMode('text')}>
                            ✍️ Switch to Text Mode
                        </button>
                    </div>
                </div>
            )}

            {/* ── MODE: TEXT / CONFIRM ── */}
            {(mode === 'text' || mode === 'confirm') && (
                <form onSubmit={handleSubmit} style={{ marginTop: '20px' }}>

                    <div className="card" style={{ marginBottom: '20px' }}>
                        {mode === 'confirm' && (
                            <div style={{
                                background: 'rgba(52,211,153,0.1)', color: 'var(--success)',
                                padding: '12px', borderRadius: '8px', marginBottom: '20px',
                                fontSize: '0.85rem', fontWeight: 600, display: 'flex', gap: '8px'
                            }}>
                                <span>✨</span> AI extracted details from your voice. Review & edit below.
                            </div>
                        )}

                        <div className="form-group">
                            <label className="form-label">Category</label>
                            <select
                                className="form-input"
                                value={form.complaint_type}
                                onChange={e => setForm({ ...form, complaint_type: e.target.value })}
                            >
                                <option value="drain">🌊 Drainage / Flooding</option>
                                <option value="road">🛣️ Road / Pothole</option>
                                <option value="transformer">⚡ Power / Transformer</option>
                                <option value="water_main">🚰 Water Supply</option>
                                <option value="toilet">🚻 Public Toilet</option>
                                <option value="park">🌳 Park / Green Space</option>
                                <option value="garbage_zone">🗑️ Garbage / Waste</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label className="form-label">Description</label>
                            <textarea
                                className="form-input"
                                rows="3" required
                                placeholder="Describe the problem clearly..."
                                value={form.description}
                                onChange={e => setForm({ ...form, description: e.target.value })}
                            ></textarea>
                        </div>

                        <div className="form-group">
                            <label className="form-label">Severity Level</label>
                            <select
                                className="form-input"
                                value={form.severity_estimate}
                                onChange={e => setForm({ ...form, severity_estimate: e.target.value })}
                            >
                                <option value="low">🟢 Low — Minor nuisance</option>
                                <option value="medium">🟡 Medium — Needs fixing soon</option>
                                <option value="high">🟠 High — Blocking daily life</option>
                                <option value="critical">🔴 Critical — Safety risk / Outage</option>
                            </select>
                        </div>

                        <div className="form-group" style={{ marginTop: '20px' }}>
                            <label className="form-label">Location (Auto-Tagged)</label>
                            <div style={{
                                display: 'flex', alignItems: 'center', gap: '12px',
                                background: 'rgba(0, 0, 0, 0.2)', padding: '12px', borderRadius: '12px',
                                border: '1px solid var(--glass-border)', backdropFilter: 'blur(8px)'
                            }}>
                                <span style={{ fontSize: '1.5rem' }}>📍</span>
                                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                    {locating ? (
                                        <span>Acquiring GPS location...</span>
                                    ) : form.lat ? (
                                        <><strong style={{ color: 'var(--success)' }}>✓ Located</strong> — {form.lat.toFixed(5)}, {form.lng.toFixed(5)}</>
                                    ) : (
                                        'Location unavailable — using ward center'
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="form-group" style={{ marginTop: '20px' }}>
                            <label className="form-label">Photo (Optional)</label>
                            <input
                                type="file"
                                accept="image/*"
                                capture="environment"
                                className="form-input"
                                style={{ paddingTop: '10px' }}
                            />
                        </div>

                    </div>

                    <button type="submit" className="btn btn-primary btn-full btn-lg">
                        🚀 Submit & Get Tracking ID
                    </button>

                    {mode === 'confirm' ? (
                        <button type="button" className="btn btn-ghost btn-full" style={{ marginTop: '12px' }} onClick={() => setMode('voice')}>
                            🎙️ Re-record Voice
                        </button>
                    ) : (
                        <button type="button" className="btn btn-ghost btn-full" style={{ marginTop: '12px' }} onClick={() => setMode('voice')}>
                            🎙️ Switch to Voice Mode
                        </button>
                    )}

                </form>
            )}
        </div>
    )
}
