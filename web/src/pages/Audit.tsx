import { useQuery } from '@tanstack/react-query'

import { api } from '../api'

export default function Audit() {
  const { data, isLoading, error } = useQuery({ queryKey: ['audit'], queryFn: api.audit })

  if (isLoading) return <p className="muted">불러오는 중…</p>
  if (error) return <p className="error">{(error as Error).message}</p>

  const entries = data ?? []
  return (
    <section>
      <h1>감사 로그</h1>
      <p className="subtitle">운영자·에이전트 쓰기 액션 기록</p>
      {entries.length === 0 ? (
        <p className="muted">감사 기록이 없습니다.</p>
      ) : (
        <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>시각</th>
              <th>행위자</th>
              <th>액션</th>
              <th>대상</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e, i) => (
              <tr key={`${e.action}-${i}`}>
                <td>{new Date(e.created_at).toLocaleString()}</td>
                <td>{e.actor}</td>
                <td>{e.action}</td>
                <td>{e.target}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </section>
  )
}
