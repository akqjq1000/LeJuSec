"""운영자 세션 정보 API."""

from fastapi import APIRouter, Request

from lejusec.auth import role_for
from lejusec.config import settings

router = APIRouter(tags=["operator"])


@router.get("/me")
def me(request: Request) -> dict[str, str]:
    """현재 요청의 운영자 역할. 인증 비활성 시 admin으로 간주한다."""
    if not settings.operator_token_map:
        return {"role": "admin", "auth": "disabled"}
    return {"role": role_for(request) or "anonymous", "auth": "enabled"}
