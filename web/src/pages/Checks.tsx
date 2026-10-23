import { useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { api, type CheckHit, type CheckItem } from '../api'

export default function Checks() {
  const [input, setInput] = useState('')
  const [query, setQuery] = useState('')

  const all = useQuery({ queryKey: ['checks'], queryFn: api.checks })
  const search = useQuery({
    queryKey: ['checks-search', query],
    queryFn: () => api.checksSearch(query),
    enabled: query.length > 0,
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    setQuery(input.trim())
  }

  return (
    <section>
      <h1>점검 기준 (RAG 근거)</h1>
      <p className="subtitle">KISA/CIS 점검 항목과 근거를 임베딩 검색</p>
      <form className="toolbar" onSubmit={submit}>
        <input
          className="input"
          placeholder="근거 검색 (예: root SSH 접속)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" className="btn-primary">
          검색
        </button>
        {query ? (
          <button
            type="button"
            onClick={() => {
              setInput('')
              setQuery('')
            }}
          >
            초기화
          </button>
        ) : null}
      </form>

      {query ? (
        search.isLoading ? (
          <p className="muted">검색 중…</p>
        ) : search.error ? (
          <p className="error">{(search.error as Error).message}</p>
        ) : (
          <HitList hits={search.data ?? []} />
        )
      ) : all.isLoading ? (
        <p className="muted">불러오는 중…</p>
      ) : all.error ? (
        <p className="error">{(all.error as Error).message}</p>
      ) : (
        <CheckList items={all.data ?? []} />
      )}
    </section>
  )
}

function CheckCard({ item, score }: { item: CheckItem; score?: number }) {
  return (
    <div className="card" style={{ textAlign: 'left' }}>
      <div>
        <span className={`badge ${item.severity}`}>{item.severity}</span>{' '}
        <strong>
          {item.id} · {item.title}
        </strong>{' '}
        <span className="muted">[{item.standard}]</span>
        {score !== undefined ? <span className="muted"> · score {score.toFixed(2)}</span> : null}
      </div>
      <p style={{ margin: '8px 0 0', fontSize: 14 }}>{item.rationale}</p>
    </div>
  )
}

function CheckList({ items }: { items: CheckItem[] }) {
  if (items.length === 0) return <p className="muted">점검 기준이 없습니다.</p>
  return (
    <div className="stack">
      {items.map((it) => (
        <CheckCard key={it.id} item={it} />
      ))}
    </div>
  )
}

function HitList({ hits }: { hits: CheckHit[] }) {
  if (hits.length === 0) return <p className="muted">관련 근거를 찾지 못했습니다.</p>
  return (
    <div className="stack">
      {hits.map((h) => (
        <CheckCard key={h.item.id} item={h.item} score={h.score} />
      ))}
    </div>
  )
}
