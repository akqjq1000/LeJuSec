import { useQuery } from '@tanstack/react-query'

import { api } from '../api'

interface Card {
  label: string
  value: number
  hint?: string
  tone?: 'ok' | 'bad' | 'warn'
}

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['summary'], queryFn: api.summary })

  if (isLoading) return <p className="muted">불러오는 중…</p>
  if (error) return <p className="error">불러오기 실패: {(error as Error).message}</p>
  if (!data) return null

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
      <div className="cards">
        {cards.map((c) => (
          <div key={c.label} className={`card ${c.tone ?? ''}`}>
            <div className="card-value">{c.value}</div>
            <div className="card-label">{c.label}</div>
            {c.hint ? <div className="card-hint">{c.hint}</div> : null}
          </div>
        ))}
      </div>
    </section>
  )
}
