"""컨트롤 플레인 API 진입점 (Phase 1 골격).

지금은 헬스체크만 제공한다. 자산 CMDB·오케스트레이터·RAG는 로드맵에 따라 추가된다.
"""

from fastapi import FastAPI

from lejusec import __version__

app = FastAPI(title="LeJuSec Control Plane", version=__version__)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """헬스체크 엔드포인트."""
    return {"status": "ok", "version": __version__}
