import { useQuery } from '@tanstack/react-query'
import { useMemo, useState, type FormEvent } from 'react'

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
      <p className="subtitle">KISA/CIS 점검 항목과 근거 — 항목을 클릭하면 전체 내용이 열립니다</p>
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
        <GroupedChecks items={all.data ?? []} />
      )}
    </section>
  )
}

function groupKey(item: CheckItem): string {
  return item.category || `${item.standard} 자동 점검`
}

/** 점검 기준을 그룹(분류)별 접이식 섹션으로 표시. */
function GroupedChecks({ items }: { items: CheckItem[] }) {
  const groups = useMemo(() => {
    const map = new Map<string, CheckItem[]>()
    for (const it of items) {
      const k = groupKey(it)
      const arr = map.get(k)
      if (arr) arr.push(it)
      else map.set(k, [it])
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0], 'ko'))
  }, [items])

  const [open, setOpen] = useState<Record<string, boolean>>({})
  const [selected, setSelected] = useState<string | null>(null)

  if (items.length === 0) return <p className="muted">점검 기준이 없습니다.</p>

  return (
    <div className="stack">
      {groups.map(([name, groupItems]) => {
        const isOpen = open[name] ?? true
        return (
          <div key={name} className="group">
            <button
              className="group-head"
              onClick={() => setOpen((o) => ({ ...o, [name]: !isOpen }))}
            >
              <span className="group-caret">{isOpen ? '▾' : '▸'}</span>
              <span className="group-name">{name}</span>
              <span className="badge">{groupItems.length}</span>
            </button>
            {isOpen ? (
              <div className="group-body">
                {groupItems.map((it) => (
                  <CheckRow
                    key={it.id}
                    item={it}
                    expanded={selected === it.id}
                    onToggle={() => setSelected(selected === it.id ? null : it.id)}
                  />
                ))}
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}

function CheckRow({
  item,
  expanded,
  onToggle,
  score,
}: {
  item: CheckItem
  expanded: boolean
  onToggle: () => void
  score?: number
}) {
  return (
    <div className="check-row">
      <button className="check-summary" onClick={onToggle} aria-expanded={expanded}>
        <span className={`badge ${item.severity}`}>{item.severity}</span>
        <strong>
          {item.id} · {item.title}
        </strong>
        <span className="muted">[{item.standard}]</span>
        {score !== undefined ? <span className="muted">score {score.toFixed(2)}</span> : null}
        <span className="check-caret">{expanded ? '접기' : '자세히'}</span>
      </button>
      {expanded ? <CheckDetail item={item} /> : null}
    </div>
  )
}

function CheckDetail({ item }: { item: CheckItem }) {
  const meta: [string, string][] = [
    ['점검 ID', item.id],
    ['기준', item.standard],
    ['분류', item.category || '-'],
    ['심각도', item.severity],
  ]
  if (item.target) meta.push(['점검 대상', item.target])
  if (item.tool) meta.push(['연동 도구', item.tool])
  if (item.rule_type) meta.push(['판정 방식', item.rule_type])

  const sections: [string, string][] = []
  if (item.purpose) sections.push(['점검 목적', item.purpose])
  if (item.threat) sections.push(['보안 위협', item.threat])
  if (item.criteria) sections.push(['판단 기준', item.criteria])
  if (item.reference) sections.push(['참고', item.reference])

  return (
    <div className="detail">
      <div className="kv compact">
        {meta.map(([k, v]) => (
          <div key={k}>
            <span className="k">{k}</span>
            <span>{v}</span>
          </div>
        ))}
      </div>

      {sections.map(([k, v]) => (
        <div key={k}>
          <div className="code-label">{k}</div>
          <p style={{ margin: '4px 0 0', whiteSpace: 'pre-wrap' }}>{v}</p>
        </div>
      ))}

      <div className="code-label">설명 · 근거</div>
      <p style={{ margin: '4px 0 0', whiteSpace: 'pre-wrap' }}>{item.rationale}</p>

      {item.fix ? (
        <>
          <div className="code-label">조치 스크립트(템플릿)</div>
          <pre>{item.fix}</pre>
        </>
      ) : null}
      {item.rollback ? (
        <>
          <div className="code-label">롤백</div>
          <pre>{item.rollback}</pre>
        </>
      ) : null}
      {!item.tool ? (
        <p className="muted" style={{ marginTop: 8 }}>
          스캐너 연동이 없는 수동 점검 항목입니다 (RAG 근거 검색 전용).
        </p>
      ) : null}
    </div>
  )
}

function HitList({ hits }: { hits: CheckHit[] }) {
  const [selected, setSelected] = useState<string | null>(null)
  if (hits.length === 0) return <p className="muted">관련 근거를 찾지 못했습니다.</p>
  return (
    <div className="stack">
      {hits.map((h) => (
        <CheckRow
          key={h.item.id}
          item={h.item}
          score={h.score}
          expanded={selected === h.item.id}
          onToggle={() => setSelected(selected === h.item.id ? null : h.item.id)}
        />
      ))}
    </div>
  )
}
