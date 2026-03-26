import localforage from 'localforage'

// Set up IndexedDB store for offline complaints
const queueStore = localforage.createInstance({
    name: 'NagarMirror',
    storeName: 'complaint_queue'
})

export const api = {
    // ── Network Utilities ──────────────────────────────────────────────────
    async fetch(endpoint, options = {}) {
        try {
            const res = await fetch(`/api${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                }
            })
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
            return await res.json()
        } catch (err) {
            console.error(`API Error on ${endpoint}:`, err)
            throw err
        }
    },

    // ── Complaints ────────────────────────────────────────────────────────
    async getComplaint(id) {
        return this.fetch(`/complaints/${id}`)
    },

    async fileComplaint(data) {
        if (!navigator.onLine) {
            // Save offline draft
            const draftId = 'draft_' + Date.now()
            const draft = { ...data, offline_draft_id: draftId, status: 'offline_pending', filed_at: new Date().toISOString() }
            await queueStore.setItem(draftId, draft)
            console.log('Saved complaint to offline queue:', draftId)
            return { ...draft, id: draftId, tracking_url: `/track/${draftId}` }
        }

        // Online submission
        return this.fetch('/complaints', {
            method: 'POST',
            body: JSON.stringify(data)
        })
    },

    async disputeResolution(id, citizen_verdict, notes = '') {
        return this.fetch(`/complaints/${id}/dispute`, {
            method: 'POST',
            body: JSON.stringify({ citizen_verdict, notes })
        })
    },

    // ── Sync Offline Queue ────────────────────────────────────────────────
    async syncQueue() {
        if (!navigator.onLine) return 0
        let synced = 0

        await queueStore.iterate(async (draft, draftId) => {
            try {
                await this.fetch('/complaints', {
                    method: 'POST',
                    body: JSON.stringify(draft)
                })
                await queueStore.removeItem(draftId)
                synced++
            } catch (err) {
                console.error('Failed to sync draft:', draftId, err)
            }
        })

        return synced
    },

    // ── Dashboard ─────────────────────────────────────────────────────────
    async getTrustScore(wardId = 'karol_bagh') {
        return this.fetch(`/trust/score/${wardId}`)
    },

    async getTrustTrend(wardId = 'karol_bagh') {
        return this.fetch(`/trust/trend/${wardId}`)
    },

    async getNarratives(wardId = 'karol_bagh') {
        return this.fetch(`/trust/narratives/${wardId}`)
    },

    async getNodes(wardId = 'karol_bagh') {
        return this.fetch(`/zones/${wardId}/nodes`)
    }
}

// Auto-sync when coming back online
window.addEventListener('online', async () => {
    console.log('Back online! Syncing queue...')
    const count = await api.syncQueue()
    if (count > 0) alert(`Synced ${count} offline complaint(s) successfully.`)
})
