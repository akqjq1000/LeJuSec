import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import Modal from '../components/Modal'
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
  const [adding, setAdding] = useState(false)

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

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>자산</h1>
          <p className="subtitle">관리 대상 시스템 목록 · 그룹별 점검 상태 (그룹 변경은 ‘자산 그룹’ 탭)</p>
        </div>
        {canWrite ? (
          <button className="btn-primary" onClick={() => setAdding(true)}>
            + 자산 추가
          </button>
        ) : null}
      </div>

      {assets.length === 0 ? (
        <p className="muted">등록된 자산이 없습니다. ‘자산 추가’로 등록하세요.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>호스트</th>
                <th>OS</th>
                <th>역할</th>
                <th>에이전트 연결</th>
                <th>최근 점검</th>
              </tr>
            </thead>
            <tbody>
              {sections.map(([name, rows]) => (
                <GroupSection key={name} name={name} rows={rows} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={adding} title="자산 추가" onClose={() => setAdding(false)}>
        <AddAssetForm
          groups={groupsQ.data ?? []}
          onDone={() => {
            setAdding(false)
            invalidate()
          }}
          onCancel={() => setAdding(false)}
        />
      </Modal>
    </section>
  )
}

function GroupSection({ name, rows }: { name: string; rows: Asset[] }) {
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
          <td>{a.role || <span className="muted">-</span>}</td>
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

function AddAssetForm({
  groups,
  onDone,
  onCancel,
}: {
  groups: string[]
  onDone: () => void
  onCancel: () => void
}) {
  const [hostname, setHostname] = useState('')
  const [role, setRole] = useState('')
  const [group, setGroup] = useState('')

  const m = useMutation({
    // OS는 입력받지 않는다 — 에이전트가 인벤토리를 보고할 때 자동 탐지된다.
    mutationFn: () =>
      api.registerAsset({ hostname: hostname.trim(), role: role.trim(), group: group.trim() }),
    onSuccess: onDone,
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (hostname.trim()) m.mutate()
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <label>
        호스트명 *
        <input
          className="input"
          autoFocus
          placeholder="예: web-01"
          value={hostname}
          onChange={(e) => setHostname(e.target.value)}
        />
      </label>
      <label>
        역할
        <input
          className="input"
          placeholder="예: 웹 서버 (선택)"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        />
      </label>
      <label>
        그룹
        <input
          className="input"
          list="add-asset-group-list"
          placeholder="기존 그룹 선택 또는 새 그룹 입력 (선택)"
          value={group}
          onChange={(e) => setGroup(e.target.value)}
        />
        <datalist id="add-asset-group-list">
          {groups.map((g) => (
            <option key={g} value={g} />
          ))}
        </datalist>
      </label>
      <p className="muted">OS는 에이전트 연결 시 자동 탐지됩니다.</p>
      {m.error ? <p className="error">{(m.error as Error).message}</p> : null}
      <div className="modal-actions">
        <button type="button" onClick={onCancel} disabled={m.isPending}>
          취소
        </button>
        <button type="submit" className="btn-primary" disabled={m.isPending || !hostname.trim()}>
          등록
        </button>
      </div>
    </form>
  )
}
