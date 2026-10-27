import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import Modal from '../components/Modal'
import { api, type Asset } from '../api'

const UNGROUPED = '미분류'

/** 자산 그룹 관리 — 그룹 추가, 그룹별 아코디언, 그룹에 자산 지정. */
export default function AssetGroups() {
  const qc = useQueryClient()
  const assetsQ = useQuery({ queryKey: ['assets'], queryFn: api.assets })
  const groupsQ = useQuery({ queryKey: ['asset-groups'], queryFn: api.assetGroups })
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const canWrite = me.data?.role === 'admin'

  const [addingGroup, setAddingGroup] = useState(false)
  const [assignTo, setAssignTo] = useState<string | null>(null)

  const assets = assetsQ.data ?? []
  const groups = groupsQ.data ?? []

  const byGroup = useMemo(() => {
    const map = new Map<string, Asset[]>()
    for (const a of assets) {
      const key = a.group || UNGROUPED
      const arr = map.get(key)
      if (arr) arr.push(a)
      else map.set(key, [a])
    }
    return map
  }, [assets])

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['assets'] })
    void qc.invalidateQueries({ queryKey: ['asset-groups'] })
  }

  if (assetsQ.isLoading) return <p className="muted">불러오는 중…</p>
  if (assetsQ.error) return <p className="error">{(assetsQ.error as Error).message}</p>

  // 레지스트리 그룹 + 미분류(자산이 있을 때)
  const names = [...groups]
  if (byGroup.has(UNGROUPED)) names.push(UNGROUPED)

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>자산 그룹</h1>
          <p className="subtitle">
            그룹을 펼쳐 소속 자산을 확인하고, 그룹별로 자산을 지정합니다
            {!canWrite ? ' (읽기 전용 역할)' : ''}
          </p>
        </div>
        {canWrite ? (
          <button className="btn-primary" onClick={() => setAddingGroup(true)}>
            + 자산 그룹 추가
          </button>
        ) : null}
      </div>

      {names.length === 0 ? (
        <p className="muted">등록된 그룹이 없습니다. ‘자산 그룹 추가’로 만드세요.</p>
      ) : (
        <div className="stack">
          {names.map((name) => (
            <GroupAccordion
              key={name}
              name={name}
              rows={byGroup.get(name) ?? []}
              canWrite={canWrite && name !== UNGROUPED}
              onAddAsset={() => setAssignTo(name)}
            />
          ))}
        </div>
      )}

      <Modal open={addingGroup} title="자산 그룹 추가" onClose={() => setAddingGroup(false)}>
        <AddGroupForm
          existing={groups}
          onDone={() => {
            setAddingGroup(false)
            invalidate()
          }}
          onCancel={() => setAddingGroup(false)}
        />
      </Modal>

      <Modal
        open={assignTo !== null}
        title={`‘${assignTo}’ 그룹에 자산 추가`}
        onClose={() => setAssignTo(null)}
      >
        {assignTo !== null ? (
          <AssignAssetsForm
            group={assignTo}
            assets={assets}
            onDone={() => {
              setAssignTo(null)
              invalidate()
            }}
            onCancel={() => setAssignTo(null)}
          />
        ) : null}
      </Modal>
    </section>
  )
}

function GroupAccordion({
  name,
  rows,
  canWrite,
  onAddAsset,
}: {
  name: string
  rows: Asset[]
  canWrite: boolean
  onAddAsset: () => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="group">
      <div className="accordion-head">
        <button className="accordion-toggle" onClick={() => setOpen((o) => !o)}>
          <span className="group-caret">{open ? '▾' : '▸'}</span>
          <span className="group-name">{name}</span>
          <span className="badge">{rows.length}</span>
        </button>
        {canWrite ? (
          <button onClick={onAddAsset} title="이 그룹에 자산 지정">
            + 자산 추가
          </button>
        ) : null}
      </div>
      {open ? (
        rows.length === 0 ? (
          <p className="muted" style={{ padding: '8px 16px' }}>
            소속 자산이 없습니다.
          </p>
        ) : (
          <ul className="tree-list bordered">
            {rows.map((a) => (
              <li key={a.id}>
                <Link to={`/assets/${a.id}`} className="tree-item">
                  <span className="tree-host">{a.hostname}</span>
                  <span className="muted">{a.os === 'pending' ? '탐지 대기' : a.os}</span>
                </Link>
              </li>
            ))}
          </ul>
        )
      ) : null}
    </div>
  )
}

function AddGroupForm({
  existing,
  onDone,
  onCancel,
}: {
  existing: string[]
  onDone: () => void
  onCancel: () => void
}) {
  const [name, setName] = useState('')
  const m = useMutation({ mutationFn: () => api.createGroup(name.trim()), onSuccess: onDone })
  const dup = existing.includes(name.trim())

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (name.trim() && !dup) m.mutate()
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <label>
        그룹명 *
        <input
          className="input"
          autoFocus
          placeholder="예: 운영-웹"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      {dup ? <p className="error">이미 존재하는 그룹입니다.</p> : null}
      {m.error ? <p className="error">{(m.error as Error).message}</p> : null}
      <div className="modal-actions">
        <button type="button" onClick={onCancel} disabled={m.isPending}>
          취소
        </button>
        <button type="submit" className="btn-primary" disabled={m.isPending || !name.trim() || dup}>
          추가
        </button>
      </div>
    </form>
  )
}

function AssignAssetsForm({
  group,
  assets,
  onDone,
  onCancel,
}: {
  group: string
  assets: Asset[]
  onDone: () => void
  onCancel: () => void
}) {
  // 이 그룹에 아직 속하지 않은 자산만 후보로 보여준다.
  const candidates = assets.filter((a) => (a.group || '') !== group)
  const [picked, setPicked] = useState<Set<number>>(new Set())

  const m = useMutation({
    mutationFn: async () => {
      for (const id of picked) await api.setGroup(id, group)
    },
    onSuccess: onDone,
  })

  const toggle = (id: number) =>
    setPicked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  return (
    <div className="form-grid">
      {candidates.length === 0 ? (
        <p className="muted">추가할 수 있는 자산이 없습니다.</p>
      ) : (
        <ul className="pick-list">
          {candidates.map((a) => (
            <li key={a.id}>
              <label className="pick-row">
                <input
                  type="checkbox"
                  checked={picked.has(a.id)}
                  onChange={() => toggle(a.id)}
                />
                <span className="tree-host">{a.hostname}</span>
                <span className="muted">{a.group || '미분류'}</span>
              </label>
            </li>
          ))}
        </ul>
      )}
      {m.error ? <p className="error">{(m.error as Error).message}</p> : null}
      <div className="modal-actions">
        <button type="button" onClick={onCancel} disabled={m.isPending}>
          취소
        </button>
        <button
          type="button"
          className="btn-primary"
          onClick={() => m.mutate()}
          disabled={m.isPending || picked.size === 0}
        >
          {picked.size > 0 ? `${picked.size}개 지정` : '지정'}
        </button>
      </div>
    </div>
  )
}
