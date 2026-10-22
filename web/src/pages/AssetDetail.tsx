import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'

import { api, type Asset } from '../api'

type Tab = 'overview' | 'inventory' | 'checks' | 'integrity' | 'remediations'

const TABS: [Tab, string][] = [
  ['overview', '개요'],
  ['inventory', '인벤토리'],
  ['checks', '점검'],
  ['integrity', '무결성'],
  ['remediations', '조치'],
]

export default function AssetDetail() {
  const params = useParams()
  const id = Number(params.id)
  const [tab, setTab] = useState<Tab>('overview')
  const asset = useQuery({ queryKey: ['asset', id], queryFn: () => api.asset(id) })

  if (asset.isLoading) return <p className="muted">불러오는 중…</p>
  if (asset.error) return <p className="error">{(asset.error as Error).message}</p>
  if (!asset.data) return null

  return (
    <section>
      <h1>{asset.data.hostname}</h1>
      <nav className="tabs">
        {TABS.map(([t, label]) => (
          <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
            {label}
          </button>
        ))}
      </nav>
      {tab === 'overview' && <Overview asset={asset.data} />}
      {tab === 'inventory' && <Inventory id={id} />}
      {tab === 'checks' && <Checks id={id} />}
      {tab === 'integrity' && <Integrity id={id} />}
      {tab === 'remediations' && <Remediations id={id} />}
    </section>
  )
}

function Overview({ asset }: { asset: Asset }) {
  const rows: [string, string][] = [
    ['호스트', asset.hostname],
    ['OS', `${asset.os} ${asset.os_version}`],
    ['역할', asset.role || '-'],
    ['관리 여부', asset.managed ? '관리 중' : '미관리'],
    ['에이전트 상태', asset.agent_status],
    ['공개키 등록', asset.public_key ? '예' : '아니오'],
    ['최근 점검', asset.last_scan_at ? new Date(asset.last_scan_at).toLocaleString() : '-'],
    ['등록 시각', new Date(asset.created_at).toLocaleString()],
  ]
  return (
    <div className="kv">
      {rows.map(([k, v]) => (
        <div key={k}>
          <span className="k">{k}</span>
          <span>{v}</span>
        </div>
      ))}
    </div>
  )
}

function Inventory({ id }: { id: number }) {
  const q = useQuery({ queryKey: ['inventory', id], queryFn: () => api.inventory(id) })
  if (q.isLoading) return <p className="muted">불러오는 중…</p>
  if (q.error || !q.data) return <p className="error">불러오기 실패</p>
  if (!q.data.captured_at) return <p className="muted">수집된 인벤토리가 없습니다.</p>
  return (
    <div className="kv">
      <div>
        <span className="k">패키지</span>
        <span>{q.data.package_count}</span>
      </div>
      <div>
        <span className="k">프로세스</span>
        <span>{q.data.process_count}</span>
      </div>
      <div>
        <span className="k">수집 시각</span>
        <span>{new Date(q.data.captured_at).toLocaleString()}</span>
      </div>
    </div>
  )
}

function Checks({ id }: { id: number }) {
  const q = useQuery({ queryKey: ['results', id], queryFn: () => api.results(id) })
  if (q.isLoading) return <p className="muted">불러오는 중…</p>
  if (q.error) return <p className="error">{(q.error as Error).message}</p>
  const results = q.data ?? []
  if (results.length === 0) return <p className="muted">점검 결과가 없습니다.</p>
  return (
    <table className="table">
      <thead>
        <tr>
          <th>항목</th>
          <th>상태</th>
          <th>심각도</th>
          <th>사유</th>
        </tr>
      </thead>
      <tbody>
        {results.map((r) => (
          <tr key={r.check_id}>
            <td>
              {r.check_id} · {r.title}
            </td>
            <td>
              <span className={`badge ${r.status}`}>{r.status}</span>
            </td>
            <td>
              <span className={`badge ${r.severity}`}>{r.severity}</span>
            </td>
            <td>{r.reason}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Integrity({ id }: { id: number }) {
  const q = useQuery({ queryKey: ['integrity', id], queryFn: () => api.integrity(id) })
  if (q.isLoading) return <p className="muted">불러오는 중…</p>
  if (q.error) return <p className="error">{(q.error as Error).message}</p>
  const events = q.data ?? []
  if (events.length === 0) return <p className="muted">무결성 변경 이벤트가 없습니다.</p>
  return (
    <table className="table">
      <thead>
        <tr>
          <th>경로</th>
          <th>변경</th>
          <th>심각도</th>
          <th>시각</th>
        </tr>
      </thead>
      <tbody>
        {events.map((e, i) => (
          <tr key={`${e.path}-${i}`}>
            <td>{e.path}</td>
            <td>{e.change_type}</td>
            <td>
              <span className={`badge ${e.severity}`}>{e.severity}</span>
            </td>
            <td>{new Date(e.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Remediations({ id }: { id: number }) {
  const q = useQuery({ queryKey: ['remediations', id], queryFn: () => api.remediations(id) })
  if (q.isLoading) return <p className="muted">불러오는 중…</p>
  if (q.error) return <p className="error">{(q.error as Error).message}</p>
  const rems = q.data ?? []
  if (rems.length === 0) return <p className="muted">생성된 조치안이 없습니다.</p>
  return (
    <table className="table">
      <thead>
        <tr>
          <th>항목</th>
          <th>상태</th>
          <th>정적분석</th>
          <th>검증</th>
        </tr>
      </thead>
      <tbody>
        {rems.map((r) => (
          <tr key={r.id}>
            <td>
              {r.check_id} · {r.title}
            </td>
            <td>{r.status}</td>
            <td>{r.static_ok ? 'OK' : `위반: ${r.static_notes}`}</td>
            <td>{r.verified ? 'OK' : '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
