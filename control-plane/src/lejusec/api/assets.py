"""자산(관리 대상 시스템) CMDB API.

시스템 등록/조회/삭제, '관리 시스템 지정(manage)·해제(unmanage)',
에이전트 공개키 등록, 서명된 인벤토리 수신을 제공한다.
"""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from lejusec.api.common import get_or_404, read_signed_body
from lejusec.auth import get_actor, record_audit
from lejusec.db import get_session
from lejusec.models import Asset, InventorySnapshot
from lejusec.schemas import (
    AssetCreate,
    AssetRead,
    InventoryAck,
    InventoryIn,
    InventorySummaryOut,
    KeyIn,
)

router = APIRouter(prefix="/assets", tags=["assets"])

SessionDep = Annotated[Session, Depends(get_session)]
Actor = Annotated[str, Depends(get_actor)]


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def register_asset(payload: AssetCreate, session: SessionDep, actor: Actor) -> AssetRead:
    """시스템을 자산으로 등록한다. hostname은 유일해야 한다."""
    exists = session.scalar(select(Asset).where(Asset.hostname == payload.hostname))
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="hostname already registered")
    asset = Asset(**payload.model_dump())
    session.add(asset)
    record_audit(session, actor, "asset.register", payload.hostname)
    session.commit()
    session.refresh(asset)
    return AssetRead.model_validate(asset)


@router.get("", response_model=list[AssetRead])
def list_assets(session: SessionDep) -> list[AssetRead]:
    assets = session.scalars(select(Asset).order_by(Asset.id)).all()
    return [AssetRead.model_validate(a) for a in assets]


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, session: SessionDep) -> AssetRead:
    return AssetRead.model_validate(get_or_404(session, asset_id))


@router.post("/{asset_id}/manage", response_model=AssetRead)
def manage_asset(asset_id: int, session: SessionDep, actor: Actor) -> AssetRead:
    """관리 시스템으로 지정한다."""
    asset = get_or_404(session, asset_id)
    asset.managed = True
    record_audit(session, actor, "asset.manage", str(asset_id))
    session.commit()
    session.refresh(asset)
    return AssetRead.model_validate(asset)


@router.post("/{asset_id}/unmanage", response_model=AssetRead)
def unmanage_asset(asset_id: int, session: SessionDep, actor: Actor) -> AssetRead:
    """관리 시스템 지정을 해제한다."""
    asset = get_or_404(session, asset_id)
    asset.managed = False
    record_audit(session, actor, "asset.unmanage", str(asset_id))
    session.commit()
    session.refresh(asset)
    return AssetRead.model_validate(asset)


@router.put("/{asset_id}/key", response_model=AssetRead)
def set_key(asset_id: int, payload: KeyIn, session: SessionDep) -> AssetRead:
    """에이전트 Ed25519 공개키를 등록/갱신한다."""
    asset = get_or_404(session, asset_id)
    asset.public_key = payload.public_key
    session.commit()
    session.refresh(asset)
    return AssetRead.model_validate(asset)


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
