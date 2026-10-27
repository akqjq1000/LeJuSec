import { useQuery } from '@tanstack/react-query'

import { AGENT_STATE_LABEL, agentState, api, type AgentState } from '../api'

interface Card {
  label: string
  value: number
  hint?: string
  tone?: 'ok' | 'bad' | 'warn'
}

const STATE_COLOR: Record<AgentState, string> = {
  connected: 'var(--ok)',
  pending: 'var(--warn)',
  unregistered: 'var(--border-strong)',
}
const STATE_ORDER: AgentState[] = ['connected', 'pending', 'unregistered']

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['summary'], queryFn: api.summary })
  const assetsQ = useQuery({ queryKey: ['assets'], queryFn: api.assets })

  if (isLoading) return <p className="muted">불러오는 중…</p>
  if (error) return <p className="error">불러오기 실패: {(error as Error).message}</p>
  if (!data) return null

  const assets = assetsQ.data ?? []
  const counts: Record<AgentState, number> = { connected: 0, pending: 0, unregistered: 0 }
  for (const a of assets) counts[agentState(a)] += 1

  const cards: Card[] = [
    { label: '자산', value: data.assets_total, hint: `관리 ${data.assets_managed}` },
    { label: '점검 통과', value: data.checks_pass, tone: 'ok' },
    { label: '점검 실패', value: data.checks_fail, tone: data.checks_fail ? 'bad' : undefined },
    { label: '비적용', value: data.checks_na },
    {
      label: '미승인 조치',
      value: data.remediations_open,
      tone: data.remediations_open ? 'warn' : undefined,
    },
    {
      label: '무결성 심각',
      value: data.integrity_high_critical,
      tone: data.integrity_high_critical ? 'bad' : 'ok',
    },
  ]

  return (
    <section>
      <h1>대시보드</h1>
      <p className="subtitle">자산·점검·조치·무결성 현황 요약</p>
      <div className="cards">
        {cards.map((c) => (
          <div key={c.label} className={`card ${c.tone ?? ''}`}>
            <div className="card-value">{c.value}</div>
            <div className="card-label">{c.label}</div>
            {c.hint ? <div className="card-hint">{c.hint}</div> : null}
          </div>
        ))}
      </div>

      <div className="section-title">에이전트 연결 현황</div>
      <div className="panel-box agent-breakdown">
        <Donut
          segments={STATE_ORDER.map((s) => ({ value: counts[s], color: STATE_COLOR[s] }))}
          total={assets.length}
        />
        <ul className="legend">
          {STATE_ORDER.map((s) => (
            <li key={s}>
              <span className="swatch" style={{ background: STATE_COLOR[s] }} />
              <span>{AGENT_STATE_LABEL[s]}</span>
              <strong>{counts[s]}</strong>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

/** 의존성 없는 인라인 SVG 도넛 차트. */
function Donut({ segments, total }: { segments: { value: number; color: string }[]; total: number }) {
  const r = 52
  const c = 2 * Math.PI * r
  let offset = 0
  return (
    <svg viewBox="0 0 140 140" width="140" height="140" role="img" aria-label="에이전트 연결 분포">
      <circle cx="70" cy="70" r={r} fill="none" stroke="var(--border)" strokeWidth="16" />
      {total > 0 &&
        segments.map((seg, i) => {
          if (seg.value === 0) return null
          const len = (seg.value / total) * c
          const dash = `${len} ${c - len}`
          const el = (
            <circle
              key={i}
              cx="70"
              cy="70"
              r={r}
              fill="none"
              stroke={seg.color}
              strokeWidth="16"
              strokeDasharray={dash}
              strokeDashoffset={-offset}
              transform="rotate(-90 70 70)"
            />
          )
          offset += len
          return el
        })}
      <text x="70" y="66" textAnchor="middle" className="donut-num">
        {total}
      </text>
      <text x="70" y="84" textAnchor="middle" className="donut-cap">
        자산
      </text>
    </svg>
  )
}
