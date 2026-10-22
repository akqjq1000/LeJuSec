"""대시보드 집계 API (운영자 콘솔용)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lejusec.db import get_session
from lejusec.models import Asset, IntegrityEventRow, RemediationRow, ScanResultRow
from lejusec.schemas import SummaryOut

router = APIRouter(tags=["summary"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/summary", response_model=SummaryOut)
def get_summary(session: SessionDep) -> SummaryOut:
    """대시보드용 전역 집계. 점검 통계는 자산별 '최근 스캔' 기준으로 합산한다."""
    assets = session.scalars(select(Asset)).all()

    checks_pass = checks_fail = checks_na = 0
    for asset in assets:
        latest = session.scalar(
            select(ScanResultRow.scan_id)
            .where(ScanResultRow.asset_id == asset.id)
            .order_by(ScanResultRow.created_at.desc(), ScanResultRow.id.desc())
            .limit(1)
        )
        if latest is None:
            continue
        rows = session.scalars(
            select(ScanResultRow).where(
                ScanResultRow.asset_id == asset.id, ScanResultRow.scan_id == latest
            )
        ).all()
        for row in rows:
            if row.status == "pass":
                checks_pass += 1
            elif row.status == "fail":
                checks_fail += 1
            else:
                checks_na += 1

    remediations_open = session.scalar(
        select(func.count()).select_from(RemediationRow).where(RemediationRow.status == "proposed")
    )
    integrity_high_critical = session.scalar(
        select(func.count())
        .select_from(IntegrityEventRow)
        .where(IntegrityEventRow.severity.in_(["critical", "high"]))
    )

    return SummaryOut(
        assets_total=len(assets),
        assets_managed=sum(1 for a in assets if a.managed),
        checks_pass=checks_pass,
        checks_fail=checks_fail,
        checks_na=checks_na,
        remediations_open=int(remediations_open or 0),
        integrity_high_critical=int(integrity_high_critical or 0),
    )
