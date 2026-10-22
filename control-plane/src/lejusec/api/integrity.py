"""파일 무결성(FIM) 수신·조회 API.

에이전트가 서명한 매니페스트를 받아 중앙 베이스라인과 비교한다. 베이스라인이 없거나
`baseline=true`면 (재)베이스라인으로 설정하고, 그 외에는 변경을 탐지해 이벤트로 저장한다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from lejusec.api.common import get_or_404, read_signed_body
from lejusec.db import get_session
from lejusec.integrity import AGENT_SELF, diff_manifest
from lejusec.models import FileBaselineRow, IntegrityEventRow
from lejusec.scanners import Severity
from lejusec.schemas import BaselineSummary, IntegrityAck, IntegrityEventOut, IntegrityIn

router = APIRouter(tags=["integrity"])

SessionDep = Annotated[Session, Depends(get_session)]


def _manifest_dict(payload: IntegrityIn) -> dict[str, str]:
    current = {entry.path: entry.sha256 for entry in payload.files}
    if payload.agent_sha256:
        current[AGENT_SELF] = payload.agent_sha256
    return current


def _load_baseline(session: Session, asset_id: int) -> dict[str, str]:
    rows = session.scalars(
        select(FileBaselineRow).where(FileBaselineRow.asset_id == asset_id)
    ).all()
    return {row.path: row.sha256 for row in rows}


def _set_baseline(session: Session, asset_id: int, current: dict[str, str]) -> None:
    session.execute(delete(FileBaselineRow).where(FileBaselineRow.asset_id == asset_id))
    for path, sha in current.items():
        session.add(FileBaselineRow(asset_id=asset_id, path=path, sha256=sha))


@router.post(
    "/assets/{asset_id}/integrity", response_model=IntegrityAck, status_code=status.HTTP_201_CREATED
)
async def ingest_integrity(
    asset_id: int,
    request: Request,
    session: SessionDep,
    baseline: bool = Query(False, description="true면 매니페스트를 새 베이스라인으로 설정"),
) -> IntegrityAck:
    asset = get_or_404(session, asset_id)
    raw = await read_signed_body(asset, request)
    payload = IntegrityIn.model_validate_json(raw)
    current = _manifest_dict(payload)

    existing = _load_baseline(session, asset_id)
    if baseline or not existing:
        _set_baseline(session, asset_id, current)
        session.commit()
        return IntegrityAck(
            baseline_established=True,
            baseline_files=len(current),
            changes=0,
            critical=0,
            high=0,
        )

    changes = diff_manifest(existing, current)
    for change in changes:
        session.add(
            IntegrityEventRow(
                asset_id=asset_id,
                path=change.path,
                change_type=change.change_type.value,
                severity=change.severity.value,
                detail=change.detail,
            )
        )
    session.commit()
    return IntegrityAck(
        baseline_established=False,
        baseline_files=len(existing),
        changes=len(changes),
        critical=sum(1 for c in changes if c.severity is Severity.CRITICAL),
        high=sum(1 for c in changes if c.severity is Severity.HIGH),
    )


@router.get("/assets/{asset_id}/integrity/baseline", response_model=BaselineSummary)
def get_baseline(asset_id: int, session: SessionDep) -> BaselineSummary:
    get_or_404(session, asset_id)
    rows = session.scalars(
        select(FileBaselineRow).where(FileBaselineRow.asset_id == asset_id)
    ).all()
    return BaselineSummary(
        files=sum(1 for r in rows if r.path != AGENT_SELF),
        has_agent_hash=any(r.path == AGENT_SELF for r in rows),
    )


@router.get("/assets/{asset_id}/integrity/events", response_model=list[IntegrityEventOut])
def list_events(
    asset_id: int,
    session: SessionDep,
    limit: int = Query(100, ge=1, le=500),
) -> list[IntegrityEventOut]:
    get_or_404(session, asset_id)
    rows = session.scalars(
        select(IntegrityEventRow)
        .where(IntegrityEventRow.asset_id == asset_id)
        .order_by(IntegrityEventRow.id.desc())
        .limit(limit)
    ).all()
    return [
        IntegrityEventOut(
            path=r.path,
            change_type=r.change_type,
            severity=r.severity,
            detail=r.detail,
            created_at=r.created_at,
        )
        for r in rows
    ]
