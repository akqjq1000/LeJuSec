import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import GroupCombo from '../components/GroupCombo'
import Modal from '../components/Modal'
import { AGENT_STATE_LABEL, agentState, api, type AgentState, type Asset } from '../api'
import { AssetDetailView } from './AssetDetail'

const STATE_DOT: Record<AgentState, string> = {
  connected: 'ok',
  pending: 'warn',
  unregistered: 'off',
}
const UNGROUPED = '미분류'

export default function Assets() {
  const qc = useQueryClient()
  const { data, isLoading, error } = useQuery({ queryKey: ['assets'], queryFn: api.assets })
  const groupsQ = useQuery({ queryKey: ['asset-groups'], queryFn: api.assetGroups })
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const canWrite = me.data?.role === 'admin'
  const [adding, setAdding] = useState(false)
  const [selected, setSelected] = useState<number | null>(null)

  const assets = useMemo(() => data ?? [], [data])

  // 선택이 없거나 사라졌으면 첫 자산을 선택.
  useEffect(() => {
    if (assets.length === 0) {
      setSelected(null)
      return
    }
    if (selected === null || !assets.some((a) => a.id === selected)) {
      setSelected(assets[0].id)
    }
  }, [assets, selected])

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
          <p className="subtitle">왼쪽 트리에서 자산을 선택하면 오른쪽에 세부 정보가 표시됩니다</p>
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
        <div className="asset-layout">
          <AssetTree sections={sections} selected={selected} onSelect={setSelected} />
          <div className="asset-detail-pane">
            {selected !== null ? (
              <AssetDetailView key={selected} id={selected} />
            ) : (
              <p className="muted">자산을 선택하세요.</p>
            )}
          </div>
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

function AssetTree({
  sections,
  selected,
  onSelect,
}: {
  sections: [string, Asset[]][]
  selected: number | null
  onSelect: (id: number) => void
}) {
  return (
    <nav className="asset-tree" aria-label="자산 트리">
      {sections.map(([name, rows]) => (
        <TreeGroup key={name} name={name} rows={rows} selected={selected} onSelect={onSelect} />
      ))}
    </nav>
  )
}

function TreeGroup({
  name,
  rows,
  selected,
  onSelect,
}: {
  name: string
  rows: Asset[]
  selected: number | null
  onSelect: (id: number) => void
}) {
  const [open, setOpen] = useState(true)
  return (
    <div className="tree-group">
      <button className="tree-group-head" onClick={() => setOpen((o) => !o)}>
        <span className="group-caret">{open ? '▾' : '▸'}</span>
        <span className="group-name">{name}</span>
        <span className="muted">{rows.length}</span>
      </button>
      {open ? (
        <ul className="tree-list">
          {rows.map((a) => (
            <li key={a.id}>
              <button
                className={`tree-item ${a.id === selected ? 'active' : ''}`}
                onClick={() => onSelect(a.id)}
              >
                <span className={`dot ${STATE_DOT[agentState(a)]}`} title={AGENT_STATE_LABEL[agentState(a)]} />
                <span className="tree-host">
                  {a.hostname.startsWith('pending-') ? a.address || a.hostname : a.hostname}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
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
  const [address, setAddress] = useState('')
  const [role, setRole] = useState('')
  const [group, setGroup] = useState('')

  const m = useMutation({
    // hostname/OS는 선택값 — 에이전트가 처음 통신할 때 서버가 자동으로 채운다.
    mutationFn: () =>
      api.registerAsset({
        hostname: hostname.trim(),
        address: address.trim(),
        role: role.trim(),
        group: group.trim(),
      }),
    onSuccess: onDone,
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    m.mutate()
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <label>
        주소(IP/도메인)
        <input
          className="input"
          autoFocus
          placeholder="예: 10.0.0.12 또는 web.example.com (선택)"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
      </label>
      <label>
        호스트명
        <input
          className="input"
          placeholder="비우면 에이전트 연결 시 자동 설정"
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
        <GroupCombo
          value={group}
          onChange={setGroup}
          options={groups}
          placeholder="기존 그룹 선택 또는 새 그룹 입력 (선택)"
        />
      </label>
      <p className="muted">호스트명·OS는 에이전트 첫 통신 시 자동으로 채워집니다.</p>
      {m.error ? <p className="error">{(m.error as Error).message}</p> : null}
      <div className="modal-actions">
        <button type="button" onClick={onCancel} disabled={m.isPending}>
          취소
        </button>
        <button type="submit" className="btn-primary" disabled={m.isPending}>
          등록
        </button>
      </div>
    </form>
  )
}
