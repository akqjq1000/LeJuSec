"""조치안 생성·검증·승인(HITL) API.

최근 점검의 불합격 항목으로 조치안을 생성(정적 분석 포함)하고, 샌드박스 드라이런
검증과 사람 승인(approve)/거부(reject)를 제공한다. 정적 분석을 통과하지 못한
조치안은 승인할 수 없다(위협 모델 T4).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from lejusec import sandbox
from lejusec.api.common import get_or_404
from lejusec.auth import get_actor, record_audit
from lejusec.db import get_session
from lejusec.generator import build_generator
from lejusec.models import RemediationRow, ScanResultRow
from lejusec.remediation import Remediation, static_analysis
from lejusec.schemas import GenerateAck, RemediationOut, VerifyOut

router = APIRouter(tags=["remediation"])

SessionDep = Annotated[Session, Depends(get_session)]
Actor = Annotated[str, Depends(get_actor)]


def _to_out(row: RemediationRow) -> RemediationOut:
    return RemediationOut(
        id=row.id,
        check_id=row.check_id,
        title=row.title,
        script=row.script,
        rollback=row.rollback,
        status=row.status,
        static_ok=row.static_ok,
        static_notes=row.static_notes,
        verified=row.verified,
        verify_notes=row.verify_notes,
    )


def _get_remediation(session: Session, remediation_id: int) -> RemediationRow:
    row = session.get(RemediationRow, remediation_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="remediation not found")
    return row


@router.post(
    "/assets/{asset_id}/remediations",
    response_model=GenerateAck,
    status_code=status.HTTP_201_CREATED,
)
def generate(asset_id: int, session: SessionDep) -> GenerateAck:
    """최근 점검의 불합격 항목으로 조치안을 생성하고 정적 분석 후 proposed로 저장한다."""
    get_or_404(session, asset_id)
    latest = session.scalar(
        select(ScanResultRow.scan_id)
        .where(ScanResultRow.asset_id == asset_id)
        .order_by(ScanResultRow.created_at.desc(), ScanResultRow.id.desc())
        .limit(1)
    )
    if latest is None:
        return GenerateAck(generated=0, proposed=[])

    failed = session.scalars(
        select(ScanResultRow).where(
            ScanResultRow.asset_id == asset_id,
            ScanResultRow.scan_id == latest,
            ScanResultRow.status == "fail",
        )
    ).all()

    rows: list[RemediationRow] = []
    for remediation in build_generator()([r.check_id for r in failed]):
        violations = static_analysis(remediation.script)
        row = RemediationRow(
            asset_id=asset_id,
            check_id=remediation.check_id,
            title=remediation.title,
            script=remediation.script,
            rollback=remediation.rollback,
            status="proposed",
            static_ok=not violations,
            static_notes="; ".join(v.reason for v in violations)[:255],
        )
        session.add(row)
        rows.append(row)
    session.commit()
    for row in rows:
        session.refresh(row)

    return GenerateAck(generated=len(rows), proposed=[_to_out(r) for r in rows])


@router.get("/assets/{asset_id}/remediations", response_model=list[RemediationOut])
def list_remediations(asset_id: int, session: SessionDep) -> list[RemediationOut]:
    get_or_404(session, asset_id)
    rows = session.scalars(
        select(RemediationRow)
        .where(RemediationRow.asset_id == asset_id)
        .order_by(RemediationRow.id)
    ).all()
    return [_to_out(r) for r in rows]


@router.post("/remediations/{remediation_id}/verify", response_model=VerifyOut)
def verify_remediation(remediation_id: int, session: SessionDep) -> VerifyOut:
    """샌드박스 드라이런으로 조치안을 검증하고 결과를 기록한다."""
    row = _get_remediation(session, remediation_id)
    result = sandbox.verify(
        Remediation(
            check_id=row.check_id, title=row.title, script=row.script, rollback=row.rollback
        )
    )
    row.verified = result.ok
    row.verify_notes = result.notes[:255]
    session.commit()
    return VerifyOut(ok=result.ok, notes=result.notes, sandbox=result.sandbox)


@router.post("/remediations/{remediation_id}/approve", response_model=RemediationOut)
def approve_remediation(remediation_id: int, session: SessionDep, actor: Actor) -> RemediationOut:
    """조치안을 승인한다(HITL). 정적 분석 위반이 있으면 승인할 수 없다."""
    row = _get_remediation(session, remediation_id)
    if row.status != "proposed":
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"not in proposed state: {row.status}")
    if not row.static_ok:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="unsafe remediation cannot be approved"
        )
    row.status = "approved"
    record_audit(session, actor, "remediation.approve", f"rid={remediation_id}")
    session.commit()
    session.refresh(row)
    return _to_out(row)


@router.post("/remediations/{remediation_id}/reject", response_model=RemediationOut)
def reject_remediation(remediation_id: int, session: SessionDep, actor: Actor) -> RemediationOut:
    """조치안을 거부한다(HITL)."""
    row = _get_remediation(session, remediation_id)
    if row.status != "proposed":
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"not in proposed state: {row.status}")
    row.status = "rejected"
    record_audit(session, actor, "remediation.reject", f"rid={remediation_id}")
    session.commit()
    session.refresh(row)
    return _to_out(row)
