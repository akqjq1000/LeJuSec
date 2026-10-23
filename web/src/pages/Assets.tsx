import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api'

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
              <th>에이전트</th>
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
                  {a.os} {a.os_version}
                </td>
                <td>{a.managed ? '관리' : '-'}</td>
                <td>{a.agent_status}</td>
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
  const [os, setOs] = useState('ubuntu')
  const [osVersion, setOsVersion] = useState('')
  const [role, setRole] = useState('')

  const m = useMutation({
    mutationFn: () =>
      api.registerAsset({ hostname: hostname.trim(), os: os.trim(), os_version: osVersion.trim(), role: role.trim() }),
    onSuccess: () => {
      setHostname('')
      setOsVersion('')
      setRole('')
      onDone()
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (hostname.trim() && os.trim()) m.mutate()
  }

  return (
    <form className="toolbar" onSubmit={submit}>
      <input
        className="input"
        placeholder="호스트명 *"
        value={hostname}
        onChange={(e) => setHostname(e.target.value)}
      />
      <input className="input sm" placeholder="OS *" value={os} onChange={(e) => setOs(e.target.value)} />
      <input
        className="input sm"
        placeholder="OS 버전"
        value={osVersion}
        onChange={(e) => setOsVersion(e.target.value)}
      />
      <input
        className="input sm"
        placeholder="역할"
        value={role}
        onChange={(e) => setRole(e.target.value)}
      />
      <button
        type="submit"
        className="btn-primary"
        disabled={m.isPending || !hostname.trim() || !os.trim()}
      >
        자산 등록
      </button>
      {m.error ? <span className="error">{(m.error as Error).message}</span> : null}
    </form>
  )
}
