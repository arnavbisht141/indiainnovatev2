import { NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'

export default function NavBar() {
    const [isOnline, setIsOnline] = useState(navigator.onLine)

    useEffect(() => {
        const handleOnline = () => setIsOnline(true)
        const handleOffline = () => setIsOnline(false)
        window.addEventListener('online', handleOnline)
        window.addEventListener('offline', handleOffline)
        return () => {
            window.removeEventListener('online', handleOnline)
            window.removeEventListener('offline', handleOffline)
        }
    }, [])

    return (
        <nav style={{
            position: 'fixed', bottom: 0, left: 0, right: 0,
            background: 'rgba(3, 7, 18, 0.65)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            borderTop: '1px solid var(--glass-border)',
            display: 'flex', justifyContent: 'space-around', padding: '12px 0 20px',
            zIndex: 100
        }}>
            <NavItem to="/" icon="🏠" label="Home" />
            <NavItem to="/file" icon="🎙️" label="File" activeColor="var(--danger)" />
            <NavItem to="/track" icon="📍" label="Track" />
            <NavItem to="/dashboard/trust" icon="📊" label="Gov" />

            {!isOnline && (
                <div style={{
                    position: 'absolute', top: '-30px', left: '50%', transform: 'translateX(-50%)',
                    background: 'var(--warning)', color: '#000', padding: '4px 12px',
                    borderRadius: '100px', fontSize: '0.75rem', fontWeight: 600,
                    boxShadow: '0 4px 12px rgba(251,191,36,0.3)'
                }}>
                    OFFLINE CACHING ACTIVE
                </div>
            )}
        </nav>
    )
}

function NavItem({ to, icon, label, activeColor = 'var(--accent)' }) {
    return (
        <NavLink
            to={to}
            style={({ isActive }) => ({
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px',
                textDecoration: 'none',
                color: isActive ? activeColor : 'var(--text-secondary)',
                transform: isActive ? 'translateY(-2px)' : 'none',
                transition: 'all var(--transition)'
            })}
        >
            <span style={{ fontSize: '1.4rem' }}>{icon}</span>
            <span style={{ fontSize: '0.7rem', fontWeight: 600 }}>{label}</span>
        </NavLink>
    )
}
