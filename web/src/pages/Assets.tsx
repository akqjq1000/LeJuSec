import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { AGENT_STATE_LABEL, agentState, api, type AgentState, type Asset } from '../api'

const STATE_BADGE: Record<AgentState, string> = {
  connected: 'pass',
  pending: 'na',
  unregistered: '',
}
const UNGROUPED = '미분류'

export default function Assets() {
  const qc = useQueryClient()
  const { data, isLoading, error } = useQuery({ queryKey: ['assets'], queryFn: api.assets })
  const groupsQ = useQuery({ queryKey: ['asset-groups'], queryFn: api.assetGroups })
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const canWrite = me.data?.role === 'admin'

  const assets = data ?? []
  // 그룹별 섹션으로 묶는다(미분류는 마지막).
  const sections = useMemo(() => {
    const map = new Map<string, Asset[]>()
    for (const a of assets) {
      const key = a.group || UNGROUPED
      const arr = map.get(key)
      if (arr) arr.push(a)
      else map.set(key, [a])
    }
    return [...map.entries()].sort((a, b) => {
      if (a[0] === UNGROUPED) return 1
      if (b[0] === UNGROUPED) return -1
      return a[0].localeCompare(b[0], 'ko')
    })
  }, [assets])

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['assets'] })
    void qc.invalidateQueries({ queryKey: ['asset-groups'] })
  }

  if (isLoading) return <p className="muted">불러오는 중…</p>
  if (error) return <p className="error">{(error as Error).message}</p>

  const knownGroups = groupsQ.data ?? []

  return (
    <section>
      <h1>자산</h1>
      <p className="subtitle">관리 대상 시스템 목록 · 그룹별 점검 상태</p>
      {canWrite ? <RegisterAssetForm groups={knownGroups} onDone={invalidate} /> : null}
      {assets.length === 0 ? (
        <p className="muted">등록된 자산이 없습니다.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>호스트</th>
                <th>OS</th>
                <th>그룹</th>
                <th>에이전트 연결</th>
                <th>최근 점검</th>
              </tr>
            </thead>
            <tbody>
              {sections.map(([name, rows]) => (
                <GroupSection
                  key={name}
                  name={name}
                  rows={rows}
                  canWrite={canWrite}
                  groups={knownGroups}
                  onChanged={invalidate}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function GroupSection({
  name,
  rows,
  canWrite,
  groups,
  onChanged,
}: {
  name: string
  rows: Asset[]
  canWrite: boolean
  groups: string[]
  onChanged: () => void
}) {
  return (
    <>
      <tr className="group-sep">
        <td colSpan={5}>
          {name} <span className="muted">· {rows.length}</span>
        </td>
      </tr>
      {rows.map((a) => (
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
          <td>
            <GroupCell asset={a} canWrite={canWrite} groups={groups} onChanged={onChanged} />
          </td>
          <td>
            <span className={`badge ${STATE_BADGE[agentState(a)]}`}>
              {AGENT_STATE_LABEL[agentState(a)]}
            </span>
          </td>
          <td>{a.last_scan_at ? new Date(a.last_scan_at).toLocaleString() : '-'}</td>
        </tr>
      ))}
    </>
  )
}

function GroupCell({
  asset,
  canWrite,
  groups,
  onChanged,
}: {
  asset: Asset
  canWrite: boolean
  groups: string[]
  onChanged: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(asset.group)
  const m = useMutation({
    mutationFn: () => api.setGroup(asset.id, value.trim()),
    onSuccess: () => {
      setEditing(false)
      onChanged()
    },
  })

  if (!canWrite) return <>{asset.group || <span className="muted">-</span>}</>
  if (!editing) {
    return (
      <button className="link-btn" onClick={() => setEditing(true)} title="그룹 변경">
        {asset.group || <span className="muted">+ 그룹</span>}
      </button>
    )
  }
  return (
    <span className="group-edit">
      <input
        className="input sm"
        list="asset-group-list"
        value={value}
        autoFocus
        placeholder="그룹명"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') m.mutate()
          if (e.key === 'Escape') setEditing(false)
        }}
      />
      <datalist id="asset-group-list">
        {groups.map((g) => (
          <option key={g} value={g} />
        ))}
      </datalist>
      <button className="btn-primary" onClick={() => m.mutate()} disabled={m.isPending}>
        저장
      </button>
      <button onClick={() => setEditing(false)}>취소</button>
    </span>
  )
}

function RegisterAssetForm({ groups, onDone }: { groups: string[]; onDone: () => void }) {
  const [hostname, setHostname] = useState('')
  const [role, setRole] = useState('')
  const [group, setGroup] = useState('')

  const m = useMutation({
    // OS는 입력받지 않는다 — 에이전트가 인벤토리를 보고할 때 자동 탐지된다.
    mutationFn: () =>
      api.registerAsset({ hostname: hostname.trim(), role: role.trim(), group: group.trim() }),
    onSuccess: () => {
      setHostname('')
      setRole('')
      setGroup('')
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
      <input
        className="input sm"
        list="register-group-list"
        placeholder="그룹 (선택)"
        value={group}
        onChange={(e) => setGroup(e.target.value)}
      />
      <datalist id="register-group-list">
        {groups.map((g) => (
          <option key={g} value={g} />
        ))}
      </datalist>
      <button type="submit" className="btn-primary" disabled={m.isPending || !hostname.trim()}>
        자산 등록
      </button>
      <span className="muted">OS는 에이전트 연결 시 자동 탐지됩니다</span>
      {m.error ? <span className="error">{(m.error as Error).message}</span> : null}
    </form>
  )
}
