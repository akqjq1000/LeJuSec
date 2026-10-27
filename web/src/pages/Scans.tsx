import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { AGENT_STATE_LABEL, agentState, api, type Asset, type CheckResult } from '../api'

const STATE_BADGE = { connected: 'pass', pending: 'na', unregistered: '' } as const

/** 점검(스캔) 탭 — 자산 전반의 최근 점검 결과를 한 화면에서 보고 검사를 요청한다. */
export default function Scans() {
  const assetsQ = useQuery({ queryKey: ['assets'], queryFn: api.assets })
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const canWrite = me.data?.role === 'admin'
  const assets = assetsQ.data ?? []

  const resultQs = useQueries({
    queries: assets.map((a) => ({
      queryKey: ['results', a.id],
      queryFn: () => api.results(a.id),
    })),
  })

  const resultsByAsset = new Map<number, CheckResult[]>()
  assets.forEach((a, i) => resultsByAsset.set(a.id, resultQs[i]?.data ?? []))

  // 점검 그룹(기준)별 필터: 결과에 존재하는 standard 집합에서 도출.
  const groups = useMemo(() => {
    const set = new Set<string>()
    for (const rs of resultsByAsset.values()) for (const r of rs) set.add(r.standard)
    return ['전체', ...[...set].sort()]
  }, [resultQs.map((q) => q.dataUpdatedAt).join(',')])
  const [group, setGroup] = useState('전체')

  const inGroup = (r: CheckResult) => group === '전체' || r.standard === group

  if (assetsQ.isLoading) return <p className="muted">불러오는 중…</p>
  if (assetsQ.error) return <p className="error">{(assetsQ.error as Error).message}</p>

  return (
    <section>
      <h1>점검</h1>
      <p className="subtitle">자산별 최근 점검 결과 요약 · 검사 요청 (개별 점검은 자산 상세에서)</p>

      <div className="toolbar">
        <span className="muted">점검 그룹</span>
        {groups.map((g) => (
          <button key={g} className={g === group ? 'btn-primary' : ''} onClick={() => setGroup(g)}>
            {g}
          </button>
        ))}
      </div>

      {assets.length === 0 ? (
        <p className="muted">등록된 자산이 없습니다.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>호스트</th>
                <th>에이전트 연결</th>
                <th>통과</th>
                <th>실패</th>
                <th>비적용</th>
                <th>최근 점검</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <ScanRow
                  key={a.id}
                  asset={a}
                  results={(resultsByAsset.get(a.id) ?? []).filter(inGroup)}
                  canWrite={canWrite}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function ScanRow({
  asset,
  results,
  canWrite,
}: {
  asset: Asset
  results: CheckResult[]
  canWrite: boolean
}) {
  const qc = useQueryClient()
  const st = agentState(asset)
  const pass = results.filter((r) => r.status === 'pass').length
  const fail = results.filter((r) => r.status === 'fail').length
  const na = results.filter((r) => r.status === 'na').length

  const requestM = useMutation({
    mutationFn: () => api.requestScan(asset.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scan-requests', asset.id] }),
  })

  return (
    <tr>
      <td>
        <Link to={`/assets/${asset.id}`}>{asset.hostname}</Link>
      </td>
      <td>
        <span className={`badge ${STATE_BADGE[st]}`}>{AGENT_STATE_LABEL[st]}</span>
      </td>
      <td>{results.length ? <span className="badge pass">{pass}</span> : '-'}</td>
      <td>{results.length ? <span className={`badge ${fail ? 'fail' : ''}`}>{fail}</span> : '-'}</td>
      <td>{results.length ? <span className="badge">{na}</span> : '-'}</td>
      <td>{asset.last_scan_at ? new Date(asset.last_scan_at).toLocaleString() : '-'}</td>
      <td>
        <button
          onClick={() => requestM.mutate()}
          disabled={requestM.isPending || !canWrite || st === 'unregistered'}
          title={st === 'unregistered' ? '에이전트 공개키 미등록' : ''}
        >
          검사 요청
        </button>
      </td>
    </tr>
  )
}
