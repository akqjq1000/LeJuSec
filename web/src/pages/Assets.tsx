import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { AGENT_STATE_LABEL, agentState, api, type AgentState } from '../api'

const STATE_BADGE: Record<AgentState, string> = {
  connected: 'pass',
  pending: 'na',
  unregistered: '',
}

export default function Assets() {
  const qc = useQueryClient()
  const { data, isLoading, error } = useQuery({ queryKey: ['assets'], queryFn: api.assets })
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const canWrite = me.data?.role === 'admin'

  if (isLoading) return <p className="muted">불러오는 중…</p>
  if (error) return <p className="error">{(error as Error).message}</p>

  const assets = data ?? []
  return (
    <section>
      <h1>자산</h1>
      <p className="subtitle">관리 대상 시스템 목록과 점검 상태</p>
      {canWrite ? (
        <RegisterAssetForm onDone={() => qc.invalidateQueries({ queryKey: ['assets'] })} />
      ) : null}
      {assets.length === 0 ? (
        <p className="muted">등록된 자산이 없습니다.</p>
      ) : (
        <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>호스트</th>
              <th>OS</th>
              <th>관리</th>
              <th>에이전트 연결</th>
              <th>최근 점검</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.id}>
                <td>
                  <Link to={`/assets/${a.id}`}>{a.hostname}</Link>
                </td>
                <td>
                  {a.os === 'pending' || a.os === '' ? (
                    <span className="muted">자동 탐지 대기</span>
                  ) : (
                    `${a.os} ${a.os_version}`.trim()
                  )}
                </td>
                <td>{a.managed ? '관리' : '-'}</td>
                <td>
                  <span className={`badge ${STATE_BADGE[agentState(a)]}`}>
                    {AGENT_STATE_LABEL[agentState(a)]}
                  </span>
                </td>
                <td>{a.last_scan_at ? new Date(a.last_scan_at).toLocaleString() : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </section>
  )
}

function RegisterAssetForm({ onDone }: { onDone: () => void }) {
  const [hostname, setHostname] = useState('')
  const [role, setRole] = useState('')

  const m = useMutation({
    // OS는 입력받지 않는다 — 에이전트가 인벤토리를 보고할 때 자동 탐지된다.
    mutationFn: () => api.registerAsset({ hostname: hostname.trim(), role: role.trim() }),
    onSuccess: () => {
      setHostname('')
      setRole('')
      onDone()
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (hostname.trim()) m.mutate()
  }

  return (
    <form className="toolbar" onSubmit={submit}>
      <input
        className="input"
        placeholder="호스트명 *"
        value={hostname}
        onChange={(e) => setHostname(e.target.value)}
      />
      <input
        className="input sm"
        placeholder="역할"
        value={role}
        onChange={(e) => setRole(e.target.value)}
      />
      <button type="submit" className="btn-primary" disabled={m.isPending || !hostname.trim()}>
        자산 등록
      </button>
      <span className="muted">OS는 에이전트 연결 시 자동 탐지됩니다</span>
      {m.error ? <span className="error">{(m.error as Error).message}</span> : null}
    </form>
  )
}
