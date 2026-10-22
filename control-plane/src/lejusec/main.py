"""컨트롤 플레인 API 진입점 (Phase 1).

헬스체크 + 자산 CMDB(등록/지정/해제). 오케스트레이터·RAG는 로드맵에 따라 추가된다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lejusec import __version__
from lejusec.api.assets import router as assets_router
from lejusec.api.checks import router as checks_router
from lejusec.api.integrity import router as integrity_router
from lejusec.api.remediations import router as remediations_router
from lejusec.api.scans import router as scans_router
from lejusec.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="LeJuSec Control Plane", version=__version__, lifespan=lifespan)
app.include_router(assets_router)
app.include_router(scans_router)
app.include_router(checks_router)
app.include_router(remediations_router)
app.include_router(integrity_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """헬스체크 엔드포인트."""
    return {"status": "ok", "version": __version__}
