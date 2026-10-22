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
| POST | `/assets/{id}/integrity` | 서명된 무결성 매니페스트 수신(베이스라인/변경 탐지) |
| GET | `/assets/{id}/integrity/events`·`/baseline` | 무결성 이벤트/베이스라인 조회 |
| DELETE | `/assets/{id}` | 등록 삭제 |

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
