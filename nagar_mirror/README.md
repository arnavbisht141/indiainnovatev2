# Nagar Mirror 🪞🌆

**Citizen Intelligence Platform for Karol Bagh Ward**

A full-stack PWA that maps city infrastructure as a Neo4j graph, lets citizens file complaints via voice, and publicly tracks government accountability via a Trust Ledger.

---

## Quick Start

### 1. Set your credentials

```bash
cp backend/.env.example .env
```

Edit `.env`:
```env
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io   # Your AuraDB URI
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

Edit `frontend/.env`:
```env
VITE_GEMINI_API_KEY=your_key     # https://aistudio.google.com/app/apikey
VITE_MAPBOX_TOKEN=your_token     # https://account.mapbox.com/access-tokens/
```

> ⚠️ The app runs in demo mode without these keys — database calls fail gracefully with mock data.

### 2. Install dependencies

```bash
# Backend
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### 3. Seed the Neo4j graph (requires credentials)

```bash
cd seed
pip install -r requirements.txt
python seed_graph.py     # Fetches Karol Bagh from OpenStreetMap → seeds 120 nodes, 160 edges
```

### 4. Start everything

```bash
bash start.sh
# → Frontend: http://localhost:5173
# → Backend:  http://localhost:8000
# → API Docs: http://localhost:8000/docs
```

---

## Architecture

```
nagar_mirror/
├── backend/              FastAPI + Neo4j async
│   └── app/
│       ├── main.py       App entrypoint + CORS
│       ├── db.py         Neo4j driver singleton
│       └── routers/
│           ├── infrastructure.py   get_node_health, cascade, zones
│           ├── complaints.py       file/track/resolve/dispute + WS
│           └── trust.py            Trust Ledger + 5-axis score
│
├── frontend/             React 19 PWA (Vite)
│   └── src/screens/
│       ├── Home.jsx              Ward health summary
│       ├── FileComplaint.jsx     Voice/text filing + Gemini NLP
│       ├── TrackComplaint.jsx    Real-time status + WebSocket
│       ├── DisputeScreen.jsx     Citizen verdict
│       ├── WardTrustScore.jsx    5-axis Radar + trend chart
│       ├── EquityMap.jsx         Mapbox infrastructure map
│       └── Narratives.jsx        Suffering Narratives
│
└── seed/
    ├── fetch_overpass.py   Pull Karol Bagh from OpenStreetMap
    └── seed_graph.py       Populate Neo4j (120 nodes, 160 edges)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Server health |
| `POST` | `/api/complaints` | File complaint |
| `GET` | `/api/complaints` | List complaints |
| `GET` | `/api/complaints/{id}` | Track complaint |
| `PUT` | `/api/complaints/{id}/resolve` | Officer resolve |
| `POST` | `/api/complaints/{id}/dispute` | Citizen verdict |
| `WS` | `/api/complaints/{id}/ws` | Real-time updates |
| `GET` | `/api/nodes/{id}/health` | Node health |
| `PUT` | `/api/nodes/{id}/health` | Update health |
| `GET` | `/api/nodes/{id}/cascade` | Cascade chain |
| `GET` | `/api/zones/{ward_id}/nodes` | Zone nodes |
| `GET` | `/api/trust/score/{ward_id}` | Trust dimensions |
| `GET` | `/api/trust/trend/{ward_id}` | 12-week trend |
| `GET` | `/api/trust/narratives/{ward_id}` | Top 5 narratives |

## Neo4j Schema

**Nodes:**  `Infrastructure {id, type, name, lat, lng, health_score, age_years, zone_type, last_maintenance_date, complaint_count}`

**Edges:** `AFFECTS {type: physical_flow|service_dependency|risk_propagation, weight, description}`

**Complaint:** `Complaint {id, complaint_type, severity_estimate, lat, lng, status, filed_at, timeline, source}`

**Trust:** `TrustLedger {id, complaint_id, ward_id, event_type, actor, recorded_at}`
