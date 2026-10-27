"""서버→에이전트 명령 채널 API (폴링 기반).

운영자가 검사 요청(scan-request)을 큐에 넣으면, 에이전트가 서명된 pull로 가져가
실행 후 서명된 report로 결과를 보고한다. 서버가 에이전트로 연결을 여는 인바운드
포트를 요구하지 않는다(기존 서명 전송 모델과 동일).

인증: `/commands/pull`·`/commands/report`는 접미사 규칙에 따라 운영자 토큰이 면제되고
서명으로 인증된다(`auth._is_agent_signed`). `/scan-requests`는 운영자 RBAC 적용.
"""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from lejusec.api.common import get_or_404, read_signed_body
from lejusec.auth import get_actor, record_audit
from lejusec.db import get_session
from lejusec.models import AgentCommandRow
from lejusec.schemas import (
    AgentCommandOut,
    CommandOut,
    CommandReportAck,
    CommandReportIn,
)

router = APIRouter(prefix="/assets", tags=["commands"])

SessionDep = Annotated[Session, Depends(get_session)]
Actor = Annotated[str, Depends(get_actor)]


def _to_out(row: AgentCommandRow) -> CommandOut:
    return CommandOut(
        id=row.id,
        kind=row.kind,
        status=row.status,
        result=row.result,
        created_at=row.created_at,
        claimed_at=row.claimed_at,
        done_at=row.done_at,
    )


@router.post(
    "/{asset_id}/scan-requests", response_model=CommandOut, status_code=status.HTTP_201_CREATED
)
def request_scan(asset_id: int, session: SessionDep, actor: Actor) -> CommandOut:
    """검사(스캔) 명령을 큐에 넣는다(운영자 admin)."""
    get_or_404(session, asset_id)
    row = AgentCommandRow(asset_id=asset_id, kind="scan", status="pending")
    session.add(row)
    record_audit(session, actor, "scan.request", str(asset_id))
    session.commit()
    session.refresh(row)
    return _to_out(row)


@router.post("/{asset_id}/scan-requests/{command_id}/cancel", response_model=CommandOut)
def cancel_scan(asset_id: int, command_id: int, session: SessionDep, actor: Actor) -> CommandOut:
    """대기/청구된 검사 요청을 취소한다(운영자 admin).

    pending은 확실히 취소되고(에이전트가 가져가지 않음), claimed는 베스트에포트로
    canceled 표시한다(이미 에이전트가 실행 중일 수 있음). 완료/실패/취소된 것은 변경 없음.
    """
    get_or_404(session, asset_id)
    row = session.get(AgentCommandRow, command_id)
    if row is None or row.asset_id != asset_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="command not found")
    if row.status in ("pending", "claimed"):
        row.status = "canceled"
        row.done_at = dt.datetime.now(dt.UTC)
        record_audit(session, actor, "scan.cancel", f"{asset_id}:{command_id}")
        session.commit()
        session.refresh(row)
    return _to_out(row)


@router.get("/{asset_id}/scan-requests", response_model=list[CommandOut])
def list_scan_requests(asset_id: int, session: SessionDep) -> list[CommandOut]:
    """최근 검사 명령 상태(운영자 조회)."""
    get_or_404(session, asset_id)
    rows = session.scalars(
        select(AgentCommandRow)
        .where(AgentCommandRow.asset_id == asset_id)
        .order_by(AgentCommandRow.id.desc())
        .limit(20)
    ).all()
    return [_to_out(r) for r in rows]


@router.post("/{asset_id}/commands/pull", response_model=list[AgentCommandOut])
async def pull_commands(
    asset_id: int, request: Request, session: SessionDep
) -> list[AgentCommandOut]:
    """에이전트가 대기 중 명령을 가져간다(서명 인증; 빈 바디). claimed로 표시."""
    asset = get_or_404(session, asset_id)
    await read_signed_body(asset, request)  # 빈 바디 서명 검증
    # 일시정지된 자산은 대기 명령을 보류한다(상태는 pending 유지 → 재개 시 디스패치).
    if asset.scan_paused:
        session.commit()  # last_seen_at 갱신은 반영
        return []
    rows = session.scalars(
        select(AgentCommandRow)
        .where(AgentCommandRow.asset_id == asset_id, AgentCommandRow.status == "pending")
        .order_by(AgentCommandRow.id)
    ).all()
    now = dt.datetime.now(dt.UTC)
    for row in rows:
        row.status = "claimed"
        row.claimed_at = now
    session.commit()
    return [AgentCommandOut(id=r.id, kind=r.kind, params=r.params) for r in rows]


@router.post("/{asset_id}/commands/report", response_model=CommandReportAck)
async def report_commands(asset_id: int, request: Request, session: SessionDep) -> CommandReportAck:
    """에이전트가 명령 실행 결과를 보고한다(서명 인증)."""
    asset = get_or_404(session, asset_id)
    raw = await read_signed_body(asset, request)
    payload = CommandReportIn.model_validate_json(raw)

    now = dt.datetime.now(dt.UTC)
    updated = 0
    for result in payload.results:
        row = session.get(AgentCommandRow, result.id)
        if row is None or row.asset_id != asset_id:
            continue
        if row.status == "canceled":
            continue  # 취소된 명령의 뒤늦은 결과 보고는 무시한다.
        row.status = result.status
        row.result = result.result[:255]
        row.done_at = now
        record_audit(session, "agent", "command.report", f"cmd={result.id} status={result.status}")
        updated += 1
    session.commit()
    return CommandReportAck(updated=updated)
