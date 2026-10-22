import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { api } from '../api'

export default function Assets() {
  const { data, isLoading, error } = useQuery({ queryKey: ['assets'], queryFn: api.assets })

  if (isLoading) return <p className="muted">불러오는 중…</p>
  if (error) return <p className="error">{(error as Error).message}</p>

  const assets = data ?? []
  return (
    <section>
      <h1>자산</h1>
      {assets.length === 0 ? (
        <p className="muted">등록된 자산이 없습니다.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>호스트</th>
              <th>OS</th>
              <th>관리</th>
              <th>에이전트</th>
              <th>최근 점검</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.id}>
                <td>
                  <Link to={`/assets/${a.id}`}>{a.hostname}</Link>
                </td>
                <td>
                  {a.os} {a.os_version}
                </td>
                <td>{a.managed ? '관리' : '-'}</td>
                <td>{a.agent_status}</td>
                <td>{a.last_scan_at ? new Date(a.last_scan_at).toLocaleString() : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
