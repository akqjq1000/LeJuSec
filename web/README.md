# Web — Operator Console (GUI G1)

LeJuSec 운영자 콘솔(읽기 전용). 컨트롤 플레인 REST API를 호출하는 SPA.
설계: [../docs/design/gui-plan.md](../docs/design/gui-plan.md).

## 개발

```bash
npm install
npm run dev        # http://localhost:5173 (API 기본 http://localhost:8000)
```

컨트롤 플레인은 CORS에서 `http://localhost:5173`을 기본 허용한다. API 주소는
`VITE_API_BASE` 환경변수로 바꿀 수 있다.

## 점검

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

## 화면 (G1, 읽기 전용)

- **대시보드**: 전역 집계(`/summary`) — 자산/관리/점검 통과·실패, 미승인 조치, 무결성 심각 이벤트
- **자산 목록**: `/assets`
- **자산 상세**: 개요 · 인벤토리 · 점검 결과 · 무결성 · 조치(읽기 전용)

조치 승인(HITL), 인증/RBAC는 G2~G4에서 추가한다.
