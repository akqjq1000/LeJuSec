import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, Route, Routes } from 'react-router-dom'

import { api, getToken, setToken } from './api'
import AssetDetail from './pages/AssetDetail'
import Assets from './pages/Assets'
import Checks from './pages/Checks'
import Dashboard from './pages/Dashboard'

function AuthControl() {
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const [token, setTok] = useState(getToken())

  const apply = () => {
    setToken(token.trim())
    window.location.reload()
  }

  return (
    <div className="auth">
      {me.error ? (
        <span className="badge fail">인증 필요</span>
      ) : me.data ? (
        <span className="badge">{me.data.role}</span>
      ) : null}
      <input
        className="input sm"
        type="password"
        placeholder="운영자 토큰"
        value={token}
        onChange={(e) => setTok(e.target.value)}
      />
      <button onClick={apply}>적용</button>
    </div>
  )
}

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
        <AuthControl />
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
