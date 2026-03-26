import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import NavBar from './components/NavBar'
import Home from './screens/Home'
import FileComplaint from './screens/FileComplaint'
import TrackComplaint from './screens/TrackComplaint'
import DisputeScreen from './screens/DisputeScreen'
import WardTrustScore from './screens/WardTrustScore'
import EquityMap from './screens/EquityMap'
import Narratives from './screens/Narratives'
import './index.css'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <NavBar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/file" element={<FileComplaint />} />
            <Route path="/track" element={<TrackComplaint />} />
            <Route path="/track/:id" element={<TrackComplaint />} />
            <Route path="/dispute/:id" element={<DisputeScreen />} />
            <Route path="/dashboard/trust" element={<WardTrustScore />} />
            <Route path="/dashboard/equity" element={<EquityMap />} />
            <Route path="/dashboard/narratives" element={<Narratives />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
