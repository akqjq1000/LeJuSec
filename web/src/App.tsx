import { Link, Route, Routes } from 'react-router-dom'

import AssetDetail from './pages/AssetDetail'
import Assets from './pages/Assets'
import Checks from './pages/Checks'
import Dashboard from './pages/Dashboard'

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">LeJuSec</span>
        <nav>
          <Link to="/">대시보드</Link>
          <Link to="/assets">자산</Link>
          <Link to="/checks">점검 기준</Link>
        </nav>
        <span className="ro-badge">read-only (G1)</span>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="/assets/:id" element={<AssetDetail />} />
          <Route path="/checks" element={<Checks />} />
        </Routes>
      </main>
    </div>
  )
}
