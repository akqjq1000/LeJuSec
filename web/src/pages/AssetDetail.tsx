import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { API_BASE, api, getToken, type Asset, type Remediation } from '../api'

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
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['integrity', id], queryFn: () => api.integrity(id) })

  // SSE: 새 무결성 이벤트가 도착하면 목록을 갱신한다.
  useEffect(() => {
    const token = getToken()
    const url = `${API_BASE}/events/integrity${token ? `?token=${encodeURIComponent(token)}` : ''}`
    const es = new EventSource(url)
    es.onmessage = () => {
      void qc.invalidateQueries({ queryKey: ['integrity', id] })
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [id, qc])

  if (q.isLoading) return <p className="muted">불러오는 중…</p>
  if (q.error) return <p className="error">{(q.error as Error).message}</p>
  const events = q.data ?? []
  return (
    <>
      <p className="muted" style={{ marginTop: 0 }}>● 실시간 감시 중 (SSE)</p>
      {events.length === 0 ? (
        <p className="muted">무결성 변경 이벤트가 없습니다.</p>
      ) : (
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
      )}
    </>
  )
}

function Remediations({ id }: { id: number }) {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['remediations', id], queryFn: () => api.remediations(id) })
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const canWrite = me.data?.role === 'admin'
  const [expanded, setExpanded] = useState<number | null>(null)

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['remediations', id] })
  }
  const genM = useMutation({ mutationFn: () => api.generateRemediations(id), onSuccess: invalidate })
  const verifyM = useMutation({
    mutationFn: (rid: number) => api.verifyRemediation(rid),
    onSuccess: invalidate,
  })
  const approveM = useMutation({
    mutationFn: (rid: number) => api.approveRemediation(rid),
    onSuccess: invalidate,
  })
  const rejectM = useMutation({
    mutationFn: (rid: number) => api.rejectRemediation(rid),
    onSuccess: invalidate,
  })

  const busy = genM.isPending || verifyM.isPending || approveM.isPending || rejectM.isPending
  const actionError =
    (genM.error as Error | null) ??
    (verifyM.error as Error | null) ??
    (approveM.error as Error | null) ??
    (rejectM.error as Error | null)
  const rems = q.data ?? []

  return (
    <div>
      <div className="toolbar">
        <button onClick={() => genM.mutate()} disabled={busy || !canWrite}>
          불합격 항목 조치안 생성
        </button>
        {!canWrite ? <span className="muted">읽기 전용 역할 — 조치 변경 권한 없음</span> : null}
        {actionError ? <span className="error">{actionError.message}</span> : null}
      </div>

      {q.isLoading ? (
        <p className="muted">불러오는 중…</p>
      ) : rems.length === 0 ? (
        <p className="muted">조치안이 없습니다. 위 버튼으로 생성하세요.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>항목</th>
              <th>상태</th>
              <th>정적분석</th>
              <th>검증</th>
              <th>적용</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rems.map((r) => (
              <RemediationRow
                key={r.id}
                r={r}
                busy={busy}
                canWrite={canWrite}
                expanded={expanded === r.id}
                onToggle={() => setExpanded(expanded === r.id ? null : r.id)}
                onVerify={() => verifyM.mutate(r.id)}
                onApprove={() => approveM.mutate(r.id)}
                onReject={() => rejectM.mutate(r.id)}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

interface RowProps {
  r: Remediation
  busy: boolean
  canWrite: boolean
  expanded: boolean
  onToggle: () => void
  onVerify: () => void
  onApprove: () => void
  onReject: () => void
}

function RemediationRow({
  r,
  busy,
  canWrite,
  expanded,
  onToggle,
  onVerify,
  onApprove,
  onReject,
}: RowProps) {
  const isProposed = r.status === 'proposed'
  return (
    <>
      <tr>
        <td>
          {r.check_id} · {r.title}
        </td>
        <td>{r.status}</td>
        <td>
          <span className={`badge ${r.static_ok ? 'pass' : 'fail'}`}>
            {r.static_ok ? 'OK' : '위반'}
          </span>
        </td>
        <td>{r.verified ? <span className="badge pass">OK</span> : '-'}</td>
        <td>{r.apply_status ? <span className="badge">{r.apply_status}</span> : '-'}</td>
        <td>
          <button onClick={onToggle}>{expanded ? '접기' : '상세'}</button>
        </td>
      </tr>
      {expanded ? (
        <tr>
          <td colSpan={6}>
            <div className="detail">
              {!r.static_ok && r.static_notes ? (
                <p className="error">정적 분석 위반: {r.static_notes}</p>
              ) : null}
              {r.verify_notes ? <p className="muted">검증: {r.verify_notes}</p> : null}
              <div className="code-label">조치 스크립트</div>
              <pre>{r.script}</pre>
              <div className="code-label">롤백</div>
              <pre>{r.rollback || '(없음)'}</pre>
              <div className="actions">
                <button onClick={onVerify} disabled={busy || !canWrite}>
                  샌드박스 검증
                </button>
                <button onClick={onApprove} disabled={busy || !canWrite || !isProposed || !r.static_ok}>
                  승인
                </button>
                <button onClick={onReject} disabled={busy || !canWrite || !isProposed}>
                  거부
                </button>
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  )
}
