"""운영자 세션 정보 + 감사 로그 API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from lejusec.auth import role_for
from lejusec.config import settings
from lejusec.db import get_session
from lejusec.models import AuditLogRow
from lejusec.schemas import AuditOut

router = APIRouter(tags=["operator"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/me")
def me(request: Request) -> dict[str, str]:
    """현재 요청의 운영자 역할. 인증 비활성 시 admin으로 간주한다."""
    if not settings.operator_token_map:
        return {"role": "admin", "auth": "disabled"}
    return {"role": role_for(request) or "anonymous", "auth": "enabled"}


@router.get("/audit", response_model=list[AuditOut])
def audit(session: SessionDep, limit: int = Query(100, ge=1, le=500)) -> list[AuditOut]:
    """최근 감사 로그(운영자 쓰기 액션)."""
    rows = session.scalars(select(AuditLogRow).order_by(AuditLogRow.id.desc()).limit(limit)).all()
    return [
        AuditOut(actor=r.actor, action=r.action, target=r.target, created_at=r.created_at)
        for r in rows
    ]
