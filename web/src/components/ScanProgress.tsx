/** 점검(스캔) 진행 과정을 단계형 프로그레스 바로 시각화한다.
 *
 * 에이전트가 폴링 기반 1회성이라 연속 퍼센트가 아닌 이산 단계로 표현한다:
 *   요청됨(pending) → 실행 중(claimed) → 완료(done) / 실패(failed) / 취소됨(canceled)
 * 진행 중(pending/claimed)에는 줄무늬 애니메이션으로 작업 중임을 나타낸다.
 */
interface Info {
  pct: number
  label: string
  tone: 'wait' | 'run' | 'done' | 'fail' | 'cancel'
}

const INFO: Record<string, Info> = {
  pending: { pct: 33, label: '요청됨 · 에이전트 폴링 대기', tone: 'wait' },
  claimed: { pct: 66, label: '실행 중 · 에이전트가 점검 수행', tone: 'run' },
  done: { pct: 100, label: '완료', tone: 'done' },
  failed: { pct: 100, label: '실패', tone: 'fail' },
  canceled: { pct: 100, label: '취소됨', tone: 'cancel' },
}

export default function ScanProgress({
  status,
  result,
}: {
  status: string
  result?: string
}) {
  const info = INFO[status] ?? { pct: 0, label: status, tone: 'wait' }
  const active = status === 'pending' || status === 'claimed'
  const label = status === 'done' && result ? `완료 · ${result}` : info.label
  return (
    <div className="scan-progress" title={label}>
      <div
        className={`progress-track tone-${info.tone}`}
        role="progressbar"
        aria-valuenow={info.pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className={`progress-fill ${active ? 'active' : ''}`}
          style={{ width: `${info.pct}%` }}
        />
      </div>
      <span className="progress-label">{label}</span>
    </div>
  )
}
