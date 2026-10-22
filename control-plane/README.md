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

## API (현재)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/healthz` | 헬스체크 |
| POST | `/assets` | 시스템 등록 |
| GET | `/assets`, `/assets/{id}` | 조회 |
| POST | `/assets/{id}/manage`·`/unmanage` | 관리 지정/해제 |
| PUT | `/assets/{id}/key` | 에이전트 Ed25519 공개키 등록 |
| POST | `/assets/{id}/inventory` | 서명된 인벤토리 수신 (X-Signature 검증) |
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
