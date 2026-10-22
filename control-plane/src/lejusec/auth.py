"""운영자 인증/인가(RBAC) 미들웨어.

운영자 콘솔/관리 엔드포인트를 베어러 토큰으로 보호한다. 역할은 admin(쓰기 허용)과
viewer(읽기 전용). 에이전트 서명 엔드포인트(인벤토리/스캔/무결성 수신)는 Ed25519
서명으로 인증되므로 운영자 토큰에서 면제한다. 쓰기 성공은 감사 로그로 남긴다.

`LEJUSEC_OPERATOR_TOKENS`가 비어 있으면 인증이 비활성(개발 편의)된다.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from lejusec.config import settings
from lejusec.models import AuditLogRow

audit_log = logging.getLogger("lejusec.audit")

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_OPEN_PATHS = frozenset({"/healthz", "/docs", "/openapi.json", "/redoc"})


def _is_agent_signed(request: Request) -> bool:
    """에이전트 서명 엔드포인트(서명으로 인증 → 운영자 토큰 면제)인지."""
    if request.method != "POST":
        return False
    return request.url.path.endswith(("/inventory", "/scan", "/integrity", "/pull", "/report"))


def role_for(request: Request) -> str | None:
    """요청의 토큰에 매핑된 역할(없으면 None).

    Authorization: Bearer 헤더를 우선 확인하고, 헤더를 설정하기 어려운 경우(SSE의
    EventSource 등)를 위해 `?token=` 쿼리 파라미터도 허용한다.
    """
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
    else:
        token = request.query_params.get("token", "")
    return settings.operator_token_map.get(token) if token else None


def get_actor(request: Request) -> str:
    """감사 기록용 행위자 식별자(인증 비활성 시 'dev')."""
    if not settings.operator_token_map:
        return "dev"
    return role_for(request) or "anonymous"


def record_audit(session: Session, actor: str, action: str, target: str = "") -> None:
    """감사 로그 1건을 세션에 추가한다(커밋은 호출자 트랜잭션에서)."""
    session.add(AuditLogRow(actor=actor, action=action, target=target))
    audit_log.info("actor=%s action=%s target=%s", actor, action, target)


class OperatorAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tokens = settings.operator_token_map
        if (
            not tokens
            or request.method == "OPTIONS"
            or request.url.path in _OPEN_PATHS
            or _is_agent_signed(request)
        ):
            return await call_next(request)

        role = role_for(request)
        if role is None:
            return JSONResponse({"detail": "operator token required"}, status_code=401)
        if request.method in _WRITE_METHODS and role != "admin":
            return JSONResponse({"detail": "admin role required"}, status_code=403)

        response = await call_next(request)
        if request.method in _WRITE_METHODS and response.status_code < 400:
            audit_log.info(
                "actor_role=%s action=%s path=%s status=%s",
                role,
                request.method,
                request.url.path,
                response.status_code,
            )
        return response
