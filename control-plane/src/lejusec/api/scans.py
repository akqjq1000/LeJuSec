"""점검(스캔) 결과 수신·조회 API.

에이전트가 수집한 스캐너 finding을 서명된 바디로 전송하면, 결정론적 룰 엔진으로
합격/불합격을 판정해 저장한다.
"""

import datetime as dt
import json
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from lejusec.api.common import get_or_404, read_signed_body
from lejusec.db import get_session
from lejusec.models import ScanResultRow
from lejusec.rules import CheckStatus, evaluate
from lejusec.schemas import CheckResultOut, ScanAck, ScanIn

router = APIRouter(prefix="/assets", tags=["scans"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/{asset_id}/scan", response_model=ScanAck, status_code=status.HTTP_201_CREATED)
async def ingest_scan(asset_id: int, request: Request, session: SessionDep) -> ScanAck:
    """서명된 스캐너 finding을 받아 룰 엔진으로 판정하고 결과를 저장한다."""
    asset = get_or_404(session, asset_id)
    raw = await read_signed_body(asset, request)

    scan_in = ScanIn.model_validate_json(raw)
    results = evaluate(list(scan_in.findings))
    scan_id = uuid4().hex
    for result in results:
        session.add(
            ScanResultRow(
                asset_id=asset.id,
                scan_id=scan_id,
                check_id=result.check_id,
                standard=result.standard,
                title=result.title,
                severity=result.severity.value,
                status=result.status.value,
                reason=result.reason,
                evidence=json.dumps(result.evidence, ensure_ascii=False),
            )
        )
    asset.last_scan_at = dt.datetime.now(dt.UTC)
    session.commit()

    return ScanAck(
        scan_id=scan_id,
        total=len(results),
        passed=sum(1 for r in results if r.status is CheckStatus.PASS),
        failed=sum(1 for r in results if r.status is CheckStatus.FAIL),
        na=sum(1 for r in results if r.status is CheckStatus.NA),
    )


@router.get("/{asset_id}/results", response_model=list[CheckResultOut])
def get_results(asset_id: int, session: SessionDep) -> list[CheckResultOut]:
    """가장 최근 스캔의 판정 결과를 반환한다."""
    get_or_404(session, asset_id)
    latest = session.scalar(
        select(ScanResultRow.scan_id)
        .where(ScanResultRow.asset_id == asset_id)
        .order_by(ScanResultRow.created_at.desc(), ScanResultRow.id.desc())
        .limit(1)
    )
    if latest is None:
        return []
    rows = session.scalars(
        select(ScanResultRow)
        .where(ScanResultRow.asset_id == asset_id, ScanResultRow.scan_id == latest)
        .order_by(ScanResultRow.id)
    ).all()
    return [
        CheckResultOut(
            check_id=row.check_id,
            standard=row.standard,
            title=row.title,
            severity=row.severity,
            status=row.status,
            reason=row.reason,
            evidence=json.loads(row.evidence),
        )
        for row in rows
    ]
