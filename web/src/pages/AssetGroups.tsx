import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { api, type Asset } from '../api'

const UNGROUPED = '미분류'

/** 자산 그룹 관리 — 그룹별로 자산을 확인하고 그룹을 지정/변경한다. */
export default function AssetGroups() {
  const assetsQ = useQuery({ queryKey: ['assets'], queryFn: api.assets })
  const groupsQ = useQuery({ queryKey: ['asset-groups'], queryFn: api.assetGroups })
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const canWrite = me.data?.role === 'admin'

  const assets = assetsQ.data ?? []
  const groups = groupsQ.data ?? []

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

  if (assetsQ.isLoading) return <p className="muted">불러오는 중…</p>
  if (assetsQ.error) return <p className="error">{(assetsQ.error as Error).message}</p>

  return (
    <section>
      <h1>자산 그룹</h1>
      <p className="subtitle">
        그룹별 자산 현황 · 그룹 지정/변경
        {!canWrite ? ' (읽기 전용 역할 — 변경 권한 없음)' : ''}
      </p>

      {assets.length === 0 ? (
        <p className="muted">등록된 자산이 없습니다.</p>
      ) : (
        <div className="stack">
          {sections.map(([name, rows]) => (
            <div key={name} className="group">
              <div className="group-head static">
                <span className="group-name">{name}</span>
                <span className="badge">{rows.length}</span>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <tbody>
                    {rows.map((a) => (
                      <tr key={a.id}>
                        <td>
                          <Link to={`/assets/${a.id}`}>{a.hostname}</Link>
                        </td>
                        <td className="muted">{a.os === 'pending' ? '탐지 대기' : a.os}</td>
                        <td style={{ textAlign: 'right' }}>
                          {canWrite ? <GroupEditor asset={a} groups={groups} /> : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function GroupEditor({ asset, groups }: { asset: Asset; groups: string[] }) {
  const qc = useQueryClient()
  const [value, setValue] = useState(asset.group)
  const m = useMutation({
    mutationFn: () => api.setGroup(asset.id, value.trim()),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['assets'] })
      void qc.invalidateQueries({ queryKey: ['asset-groups'] })
    },
  })
  const dirty = value.trim() !== asset.group
  return (
    <span className="group-edit">
      <input
        className="input sm"
        list="group-mgmt-list"
        value={value}
        placeholder="그룹명 (비우면 미분류)"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && dirty) m.mutate()
        }}
      />
      <datalist id="group-mgmt-list">
        {groups.map((g) => (
          <option key={g} value={g} />
        ))}
      </datalist>
      <button
        className="btn-primary"
        onClick={() => m.mutate()}
        disabled={m.isPending || !dirty}
      >
        적용
      </button>
    </span>
  )
}
