import { useMutation, useQueries, useQuery, useQueryClient, type Query } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  AGENT_STATE_LABEL,
  HEALTH_LABEL,
  agentState,
  api,
  type Asset,
  type AssetHealth,
  type CheckResult,
  type Command,
} from '../api'

const STATE_BADGE = { connected: 'pass', pending: 'na', unregistered: '' } as const
const HEALTH_BADGE: Record<AssetHealth, string> = {
  online: 'pass',
  stale: 'na',
  offline: 'fail',
  unknown: '',
}
const HEALTH_DOT: Record<AssetHealth, string> = {
  online: 'ok',
  stale: 'warn',
  offline: 'off',
  unknown: 'off',
}

/** 상대 시각 표기(헬스 "최근 확인"용). */
function sinceLabel(iso: string | null): string {
  if (!iso) return '확인 없음'
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.max(0, Math.floor(diff / 1000))
  if (s < 60) return `${s}초 전`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}분 전`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}시간 전`
  return `${Math.floor(h / 24)}일 전`
}

/** 점검(스캔) 탭 — 자산 전반의 최근 점검 결과·헬스를 한 화면에서 보고 검사를 제어한다. */
export default function Scans() {
  const assetsQ = useQuery({
    queryKey: ['assets'],
    queryFn: api.assets,
    refetchInterval: 15000, // 헬스 상태를 주기적으로 갱신
  })
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const canWrite = me.data?.role === 'admin'
  const assets = useMemo(() => assetsQ.data ?? [], [assetsQ.data])

  const resultQs = useQueries({
    queries: assets.map((a) => ({
      queryKey: ['results', a.id],
      queryFn: () => api.results(a.id),
    })),
  })
  const reqQs = useQueries({
    queries: assets.map((a) => ({
      queryKey: ['scan-requests', a.id],
      queryFn: () => api.scanRequests(a.id),
      refetchInterval: (query: Query) => {
        const list = (query.state.data as Command[] | undefined) ?? []
        return list.some((c) => c.status === 'pending' || c.status === 'claimed') ? 3000 : false
      },
    })),
  })

  const resultsByAsset = new Map<number, CheckResult[]>()
  const reqsByAsset = new Map<number, Command[]>()
  assets.forEach((a, i) => {
    resultsByAsset.set(a.id, resultQs[i]?.data ?? [])
    reqsByAsset.set(a.id, reqQs[i]?.data ?? [])
  })

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
      <p className="subtitle">
        자산별 헬스·최근 점검 결과 · 검사 제어 (개별 점검 상세는 자산 상세에서)
      </p>

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
                <th>자산 (주소 · 호스트)</th>
                <th>헬스</th>
                <th>에이전트</th>
                <th>통과</th>
                <th>실패</th>
                <th>비적용</th>
                <th>최근 점검</th>
                <th>검사 제어</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <ScanRow
                  key={a.id}
                  asset={a}
                  results={(resultsByAsset.get(a.id) ?? []).filter(inGroup)}
                  requests={reqsByAsset.get(a.id) ?? []}
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
  requests,
  canWrite,
}: {
  asset: Asset
  results: CheckResult[]
  requests: Command[]
  canWrite: boolean
}) {
  const qc = useQueryClient()
  const st = agentState(asset)
  const pass = results.filter((r) => r.status === 'pass').length
  const fail = results.filter((r) => r.status === 'fail').length
  const na = results.filter((r) => r.status === 'na').length
  const pending = requests.find((c) => c.status === 'pending' || c.status === 'claimed')

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['scan-requests', asset.id] })
    void qc.invalidateQueries({ queryKey: ['assets'] })
  }
  const requestM = useMutation({ mutationFn: () => api.requestScan(asset.id), onSuccess: invalidate })
  const cancelM = useMutation({
    mutationFn: (cmdId: number) => api.cancelScan(asset.id, cmdId),
    onSuccess: invalidate,
  })
  const pauseM = useMutation({
    mutationFn: () => (asset.scan_paused ? api.resumeScans(asset.id) : api.pauseScans(asset.id)),
    onSuccess: invalidate,
  })
  const busy = requestM.isPending || cancelM.isPending || pauseM.isPending

  return (
    <tr>
      <td>
        <Link to={`/assets/${asset.id}`}>{asset.address || asset.hostname}</Link>
        {asset.address ? <div className="muted sub">{asset.hostname}</div> : null}
      </td>
      <td>
        <span className={`badge ${HEALTH_BADGE[asset.health]}`} title={sinceLabel(asset.last_seen_at)}>
          <span className={`dot ${HEALTH_DOT[asset.health]}`} /> {HEALTH_LABEL[asset.health]}
        </span>
        <div className="muted sub">{sinceLabel(asset.last_seen_at)}</div>
      </td>
      <td>
        <span className={`badge ${STATE_BADGE[st]}`}>{AGENT_STATE_LABEL[st]}</span>
      </td>
      <td>{results.length ? <span className="badge pass">{pass}</span> : '-'}</td>
      <td>{results.length ? <span className={`badge ${fail ? 'fail' : ''}`}>{fail}</span> : '-'}</td>
      <td>{results.length ? <span className="badge">{na}</span> : '-'}</td>
      <td>{asset.last_scan_at ? new Date(asset.last_scan_at).toLocaleString() : '-'}</td>
      <td>
        <div className="row-actions">
          {asset.scan_paused ? <span className="badge na">일시정지됨</span> : null}
          <button
            onClick={() => requestM.mutate()}
            disabled={busy || !canWrite || st === 'unregistered' || asset.scan_paused}
            title={
              asset.scan_paused
                ? '일시정지 상태 — 재개 후 요청'
                : st === 'unregistered'
                  ? '에이전트 공개키 미등록'
                  : ''
            }
          >
            검사 요청
          </button>
          {pending ? (
            <button className="btn-danger" onClick={() => cancelM.mutate(pending.id)} disabled={busy || !canWrite}>
              취소
            </button>
          ) : null}
          <button onClick={() => pauseM.mutate()} disabled={busy || !canWrite}>
            {asset.scan_paused ? '재개' : '일시정지'}
          </button>
        </div>
      </td>
    </tr>
  )
}
