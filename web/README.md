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
- **자산 상세**: 개요 · 인벤토리 · 점검 결과 · 무결성 · **조치(HITL)**
  - 조치 탭(G2): 조치안 생성, 스크립트/롤백 미리보기, 샌드박스 검증, 승인/거부
    (정적 분석 위반 조치는 승인 비활성화)

- **점검 기준(G3)**: 기준 목록 + RAG 근거 검색(`/checks/search`)

- **운영자 인증(G4)**: 상단바 토큰 입력(localStorage 저장) → `Authorization: Bearer`
  전송. 역할(admin/viewer)이 표시되며, viewer는 조치 변경 버튼이 비활성화된다.
  (백엔드가 `LEJUSEC_OPERATOR_TOKENS` 미설정이면 인증 비활성 → admin으로 동작.)

무결성 실시간 알림(SSE)·다크모드·i18n은 추후 추가한다.
