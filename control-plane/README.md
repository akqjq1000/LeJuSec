# Control Plane

LeJuSec 컨트롤 플레인 — API, 오케스트레이터, RAG, 자산 CMDB.
전체 설계는 [../docs/architecture.md](../docs/architecture.md) 참고.

## 개발

```bash
uv venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
cp .env.example .env
uvicorn lejusec.main:app --reload         # http://127.0.0.1:8000/healthz
```

## 점검

```bash
ruff check . && ruff format --check . && mypy src tests
pytest -q
```

## 실행 / mTLS

```bash
# 평문 HTTP (개발)
python -m lejusec.server

# 상호 TLS: 개발용 인증서 생성 후 mTLS로 기동
python scripts/gen_certs.py --out ../certs --server-san DNS:localhost --server-san IP:127.0.0.1
LEJUSEC_TLS_CERTFILE=../certs/server.crt \
LEJUSEC_TLS_KEYFILE=../certs/server.key \
LEJUSEC_TLS_CA_CERTS=../certs/ca.crt \
python -m lejusec.server     # 클라이언트 인증서를 요구(CERT_REQUIRED)
```

CA/서버/클라이언트 개인키(`*.key`)는 `.gitignore`로 커밋되지 않는다. 운영에서는
사내 PKI/ACME로 대체한다.

## API (현재)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/healthz` | 헬스체크 |
| POST | `/assets` | 시스템 등록 |
| GET | `/assets`, `/assets/{id}` | 조회 |
| POST | `/assets/{id}/manage`·`/unmanage` | 관리 지정/해제 |
| PUT | `/assets/{id}/key` | 에이전트 Ed25519 공개키 등록 |
| POST | `/assets/{id}/inventory` | 서명된 인벤토리 수신 (X-Signature 검증) |
| POST | `/assets/{id}/scan` | 서명된 스캐너 finding 수신 → 룰 엔진 판정·저장 |
| GET | `/assets/{id}/results` | 최근 점검 판정 결과 |
| GET | `/checks` | 점검 기준 목록 |
| GET | `/checks/search?q=` | RAG 근거 검색 |
| POST | `/assets/{id}/remediations` | 불합격 항목 조치안 생성(정적 분석) |
| GET | `/assets/{id}/remediations` | 조치안 목록 |
| POST | `/remediations/{rid}/verify` | 샌드박스 드라이런 검증 |
| POST | `/remediations/{rid}/approve`·`/reject` | HITL 승인/거부 (unsafe는 승인 불가) |
| POST | `/assets/{id}/remediations/pull`·`/report` | 에이전트: 승인 조치 수신 / 적용 결과 보고 (서명) |
| POST·GET | `/assets/{id}/scan-requests` | 운영자: 원격 검사(스캔) 요청 큐잉 / 상태 조회 |
| POST | `/assets/{id}/commands/pull`·`/report` | 에이전트: 대기 명령 수신 / 실행 결과 보고 (서명) |
| POST | `/assets/{id}/integrity` | 서명된 무결성 매니페스트 수신(베이스라인/변경 탐지) |
| GET | `/assets/{id}/integrity/events`·`/baseline` | 무결성 이벤트/베이스라인 조회 |
| GET | `/me` | 현재 운영자 역할 |
| GET | `/audit` | 감사 로그(운영자 쓰기 액션) |
| GET | `/events/integrity` | 무결성 변경 실시간 스트림(SSE; `once=true`로 백필) |
| DELETE | `/assets/{id}` | 등록 삭제 |

### 운영자 인증(RBAC)

`LEJUSEC_OPERATOR_TOKENS`(예: `admintok:admin,viewtok:viewer`)를 설정하면 운영자
엔드포인트가 베어러 토큰으로 보호된다. `admin`은 쓰기, `viewer`는 읽기 전용이며,
에이전트 서명 엔드포인트(인벤토리/스캔/무결성 수신)는 서명으로 인증되어 면제된다.
비우면 인증 비활성(개발). 쓰기 성공은 `lejusec.audit` 로거로 감사 기록된다.

### 조치 생성기

`LEJUSEC_GENERATOR_BACKEND`(`template` 기본 | `llm`). `llm` + `LEJUSEC_LLM_API_KEY`
설정 시 Claude(`LEJUSEC_LLM_MODEL`, 기본 `claude-opus-5-5`)로 조치를 생성한다
(`pip install -e ".[llm]"` 필요). LLM 출력이 정적 분석을 통과하지 못하거나 호출이
실패하면 템플릿으로 폴백한다.

### 샌드박스 검증

`LEJUSEC_SANDBOX_BACKEND`(`dry-run` 기본 | `container`). `container`는 격리된 Docker
컨테이너(`--network=none`, 메모리/PID 제한)에서 조치 스크립트를 실제 적용해 오류 없이
수행되는지 확인한다(`LEJUSEC_SANDBOX_IMAGE`, 기본 `ubuntu:24.04`). 어느 백엔드든 조치는
먼저 정적 분석을 통과해야 한다.

## 구조

```
src/lejusec/
  main.py      # FastAPI 앱
  config.py    # 설정 (LEJUSEC_* 환경변수 / .env)
  models.py    # Asset, InventorySnapshot (SQLAlchemy)
  schemas.py   # Pydantic 스키마
  signing.py   # Ed25519 서명 검증
  api/assets.py
tests/
```
