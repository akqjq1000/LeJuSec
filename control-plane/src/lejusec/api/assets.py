"""자산(관리 대상 시스템) CMDB API.

시스템 등록/조회/삭제, '관리 시스템 지정(manage)·해제(unmanage)',
에이전트 공개키 등록, 서명된 인벤토리 수신을 제공한다.
"""

import datetime as dt
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from lejusec.api.common import client_ip, get_or_404, read_signed_body
from lejusec.auth import get_actor, record_audit
from lejusec.db import get_session
from lejusec.models import Asset, InventorySnapshot
from lejusec.schemas import (
    AssetCreate,
    AssetRead,
    GroupIn,
    HeartbeatAck,
    HostIn,
    InventoryAck,
    InventoryIn,
    InventorySummaryOut,
    KeyIn,
)

router = APIRouter(prefix="/assets", tags=["assets"])

SessionDep = Annotated[Session, Depends(get_session)]
Actor = Annotated[str, Depends(get_actor)]


def _autofill_identity(asset: Asset, host: HostIn, ip: str, session: Session) -> None:
    """에이전트 보고 호스트 정보로 자산의 os/hostname/address를 자동으로 채운다."""
    if host.os:
        asset.os = host.os[:64]
        if host.os_version:
            asset.os_version = host.os_version[:64]
    # hostname: 임시 식별자(pending-)인 경우에만, 보고된 이름이 비어 있지 않고
    # 다른 자산과 충돌하지 않을 때 교체한다.
    reported = (host.hostname or "").strip()
    if reported and asset.hostname.startswith("pending-"):
        taken = session.scalar(
            select(Asset).where(Asset.hostname == reported, Asset.id != asset.id)
        )
        if taken is None:
            asset.hostname = reported[:255]
    # address: 에이전트가 보고한 주소를 우선, 없으면 요청 소스 IP를 폴백으로 기록한다.
    address = (host.address or "").strip() or ip
    if address:
        asset.address = address[:255]


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def register_asset(payload: AssetCreate, session: SessionDep, actor: Actor) -> AssetRead:
    """시스템을 자산으로 등록한다.

    hostname을 비워 두면 임시 식별자(`pending-xxxx`)를 부여한다. 에이전트가 처음
    통신(인벤토리)하면 서버가 실제 hostname/주소를 자동으로 채운다.
    """
    data = payload.model_dump()
    hostname = (data.get("hostname") or "").strip()
    if hostname:
        exists = session.scalar(select(Asset).where(Asset.hostname == hostname))
        if exists is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="hostname already registered")
        data["hostname"] = hostname
    else:
        # 임시 식별자(유일). 첫 인벤토리에서 실제 hostname으로 교체된다.
        data["hostname"] = f"pending-{uuid4().hex[:8]}"
    # OS를 입력하지 않으면 "pending"으로 두고, 에이전트 인벤토리에서 자동 탐지해 채운다.
    if not data.get("os"):
        data["os"] = "pending"
    asset = Asset(**data)
    session.add(asset)
    record_audit(session, actor, "asset.register", data["hostname"])
    session.commit()
    session.refresh(asset)
    return AssetRead.from_asset(asset)


@router.get("", response_model=list[AssetRead])
def list_assets(session: SessionDep) -> list[AssetRead]:
    assets = session.scalars(select(Asset).order_by(Asset.id)).all()
    return [AssetRead.from_asset(a) for a in assets]


@router.get("/groups", response_model=list[str])
def list_groups(session: SessionDep) -> list[str]:
    """등록된 자산 그룹명 목록(중복 제거, 빈 값 제외). 그룹 선택 UI용."""
    rows = session.scalars(select(Asset.group).where(Asset.group != "").distinct()).all()
    return sorted(rows)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, session: SessionDep) -> AssetRead:
    return AssetRead.from_asset(get_or_404(session, asset_id))


@router.put("/{asset_id}/group", response_model=AssetRead)
def set_group(asset_id: int, payload: GroupIn, session: SessionDep, actor: Actor) -> AssetRead:
    """기존 자산의 그룹을 지정/변경한다(빈 값이면 그룹 해제)."""
    asset = get_or_404(session, asset_id)
    asset.group = payload.group.strip()
    record_audit(session, actor, "asset.group", f"{asset_id}:{asset.group or '-'}")
    session.commit()
    session.refresh(asset)
    return AssetRead.from_asset(asset)


@router.post("/{asset_id}/manage", response_model=AssetRead)
def manage_asset(asset_id: int, session: SessionDep, actor: Actor) -> AssetRead:
    """관리 시스템으로 지정한다."""
    asset = get_or_404(session, asset_id)
    asset.managed = True
    record_audit(session, actor, "asset.manage", str(asset_id))
    session.commit()
    session.refresh(asset)
    return AssetRead.from_asset(asset)


@router.post("/{asset_id}/unmanage", response_model=AssetRead)
def unmanage_asset(asset_id: int, session: SessionDep, actor: Actor) -> AssetRead:
    """관리 시스템 지정을 해제한다."""
    asset = get_or_404(session, asset_id)
    asset.managed = False
    record_audit(session, actor, "asset.unmanage", str(asset_id))
    session.commit()
    session.refresh(asset)
    return AssetRead.from_asset(asset)


@router.put("/{asset_id}/key", response_model=AssetRead)
def set_key(asset_id: int, payload: KeyIn, session: SessionDep) -> AssetRead:
    """에이전트 Ed25519 공개키를 등록/갱신한다."""
    asset = get_or_404(session, asset_id)
    asset.public_key = payload.public_key
    session.commit()
    session.refresh(asset)
    return AssetRead.from_asset(asset)


@router.post("/{asset_id}/heartbeat", response_model=HeartbeatAck)
async def heartbeat(asset_id: int, request: Request, session: SessionDep) -> HeartbeatAck:
    """경량 헬스체크(서명된 빈 바디). last_seen_at만 갱신해 생존을 알린다."""
    asset = get_or_404(session, asset_id)
    await read_signed_body(asset, request)  # 서명 검증 + last_seen_at 갱신
    asset.agent_status = "reporting"
    # 보고된 소스 IP가 있고 주소가 아직 없으면 폴백으로 채운다.
    if not asset.address:
        ip = client_ip(request)
        if ip:
            asset.address = ip[:255]
    session.commit()
    session.refresh(asset)
    return HeartbeatAck(asset_id=asset.id, seen_at=asset.last_seen_at or dt.datetime.now(dt.UTC))


@router.post("/{asset_id}/scans/pause", response_model=AssetRead)
def pause_scans(asset_id: int, session: SessionDep, actor: Actor) -> AssetRead:
    """이 자산의 점검 디스패치를 일시정지한다(대기 명령은 pull에서 보류)."""
    asset = get_or_404(session, asset_id)
    asset.scan_paused = True
    record_audit(session, actor, "scan.pause", str(asset_id))
    session.commit()
    session.refresh(asset)
    return AssetRead.from_asset(asset)


@router.post("/{asset_id}/scans/resume", response_model=AssetRead)
def resume_scans(asset_id: int, session: SessionDep, actor: Actor) -> AssetRead:
    """이 자산의 점검 디스패치를 재개한다."""
    asset = get_or_404(session, asset_id)
    asset.scan_paused = False
    record_audit(session, actor, "scan.resume", str(asset_id))
    session.commit()
    session.refresh(asset)
    return AssetRead.from_asset(asset)


@router.post(
    "/{asset_id}/inventory", response_model=InventoryAck, status_code=status.HTTP_201_CREATED
)
async def ingest_inventory(asset_id: int, request: Request, session: SessionDep) -> InventoryAck:
    """서명된 인벤토리를 수신한다 (X-Signature를 전송 바디 바이트에 대해 검증)."""
    asset = get_or_404(session, asset_id)
    raw = await read_signed_body(asset, request)

    inv = InventoryIn.model_validate_json(raw)
    snapshot = InventorySnapshot(
        asset_id=asset.id,
        package_count=len(inv.packages),
        process_count=len(inv.processes),
        payload=raw.decode("utf-8"),
    )
    asset.last_scan_at = dt.datetime.now(dt.UTC)
    asset.agent_status = "reporting"
    # OS/식별자 자동 탐지: 에이전트 보고를 신뢰 소스로 삼아 자산 필드를 채운다.
    # (운영자가 등록 시 OS/hostname을 입력하지 않아도 되도록 한다.)
    if inv.host is not None:
        _autofill_identity(asset, inv.host, client_ip(request), session)
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return InventoryAck(
        snapshot_id=snapshot.id,
        package_count=snapshot.package_count,
        process_count=snapshot.process_count,
        captured_at=snapshot.captured_at,
    )


@router.get("/{asset_id}/inventory", response_model=InventorySummaryOut)
def get_inventory(asset_id: int, session: SessionDep) -> InventorySummaryOut:
    """최근 인벤토리 스냅샷 요약(패키지/프로세스 수)."""
    get_or_404(session, asset_id)
    snapshot = session.scalar(
        select(InventorySnapshot)
        .where(InventorySnapshot.asset_id == asset_id)
        .order_by(InventorySnapshot.id.desc())
        .limit(1)
    )
    if snapshot is None:
        return InventorySummaryOut(package_count=0, process_count=0, captured_at=None)
    return InventorySummaryOut(
        package_count=snapshot.package_count,
        process_count=snapshot.process_count,
        captured_at=snapshot.captured_at,
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def deregister_asset(asset_id: int, session: SessionDep, actor: Actor) -> None:
    """자산 등록을 삭제한다."""
    asset = get_or_404(session, asset_id)
    record_audit(session, actor, "asset.deregister", str(asset_id))
    session.delete(asset)
    session.commit()
