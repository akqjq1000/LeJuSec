"""컨트롤 플레인 API 진입점 (Phase 1).

헬스체크 + 자산 CMDB(등록/지정/해제). 오케스트레이터·RAG는 로드맵에 따라 추가된다.
"""

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import resources

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

from lejusec import __version__
from lejusec.api.assets import router as assets_router
from lejusec.api.checks import router as checks_router
from lejusec.api.commands import router as commands_router
from lejusec.api.groups import router as groups_router
from lejusec.api.integrity import router as integrity_router
from lejusec.api.operator import router as operator_router
from lejusec.api.remediations import router as remediations_router
from lejusec.api.scans import router as scans_router
from lejusec.api.summary import router as summary_router
from lejusec.auth import OperatorAuthMiddleware
from lejusec.config import settings
from lejusec.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="LeJuSec Control Plane", version=__version__, lifespan=lifespan)

# 미들웨어는 나중에 추가한 것이 바깥쪽. CORS를 바깥에 두어 인증 실패(401/403)
# 응답에도 CORS 헤더가 붙도록 인증 미들웨어를 먼저 추가한다.
app.add_middleware(OperatorAuthMiddleware)
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(assets_router)
app.include_router(groups_router)
app.include_router(commands_router)
app.include_router(scans_router)
app.include_router(checks_router)
app.include_router(remediations_router)
app.include_router(integrity_router)
app.include_router(summary_router)
app.include_router(operator_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """헬스체크 엔드포인트."""
    return {"status": "ok", "version": __version__}


@app.get("/install.sh", response_class=PlainTextResponse)
def install_script(request: Request) -> str:
    """에이전트 원샷 설치 스크립트. 대상 시스템에서 한 줄로 실행한다:

        curl -fsSL <이 주소>/install.sh | sudo bash -s -- --group 운영-웹

    스크립트의 서버 주소 자리표시자를 이 요청의 베이스 URL로 치환해 내려준다.
    """
    script = resources.files("lejusec.assets").joinpath("install-agent.sh").read_text("utf-8")
    base = str(request.base_url).rstrip("/")
    return script.replace("@@DEFAULT_SERVER@@", base)


# 에이전트 바이너리 파일명 형식: lejusec-agent-<os>-<arch> (경로 조작 방지).
_AGENT_BIN_RE = re.compile(r"^lejusec-agent-[a-z0-9]+-[a-z0-9]+$")


@app.get("/agent/{filename}")
def agent_binary(filename: str) -> FileResponse:
    """빌드된 에이전트 바이너리를 제공한다(설치 스크립트가 내려받음).

    `make agent-dist` 로 만든 dist/lejusec-agent-linux-{amd64,arm64} 를 서빙한다.
    디렉터리에 바이너리가 없으면 404 — 설치 스크립트는 GitHub 릴리스로 폴백한다.
    """
    if not _AGENT_BIN_RE.match(filename):
        raise HTTPException(status_code=404, detail="not found")
    path = settings.agent_dist_path / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="agent binary not published")
    return FileResponse(path, media_type="application/octet-stream", filename=filename)
