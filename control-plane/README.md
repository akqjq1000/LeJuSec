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

## 구조

```
src/lejusec/
  main.py      # FastAPI 앱 (현재: /healthz)
  config.py    # 설정 (LEJUSEC_* 환경변수 / .env)
tests/
```
