"""자산(관리 대상 시스템) CMDB API.

시스템 등록/조회/삭제, '관리 시스템 지정(manage)·해제(unmanage)',
에이전트 공개키 등록, 서명된 인벤토리 수신을 제공한다.
"""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from lejusec.db import get_session
from lejusec.models import Asset, InventorySnapshot
from lejusec.schemas import AssetCreate, AssetRead, InventoryAck, InventoryIn, KeyIn
from lejusec.signing import verify_ed25519

router = APIRouter(prefix="/assets", tags=["assets"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_or_404(session: Session, asset_id: int) -> Asset:
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="asset not found")
    return asset


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def register_asset(payload: AssetCreate, session: SessionDep) -> AssetRead:
    """시스템을 자산으로 등록한다. hostname은 유일해야 한다."""
    exists = session.scalar(select(Asset).where(Asset.hostname == payload.hostname))
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="hostname already registered")
    asset = Asset(**payload.model_dump())
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return AssetRead.model_validate(asset)


@router.get("", response_model=list[AssetRead])
def list_assets(session: SessionDep) -> list[AssetRead]:
    assets = session.scalars(select(Asset).order_by(Asset.id)).all()
    return [AssetRead.model_validate(a) for a in assets]


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, session: SessionDep) -> AssetRead:
    return AssetRead.model_validate(_get_or_404(session, asset_id))


@router.post("/{asset_id}/manage", response_model=AssetRead)
def manage_asset(asset_id: int, session: SessionDep) -> AssetRead:
    """관리 시스템으로 지정한다."""
    asset = _get_or_404(session, asset_id)
    asset.managed = True
    session.commit()
    session.refresh(asset)
    return AssetRead.model_validate(asset)


@router.post("/{asset_id}/unmanage", response_model=AssetRead)
def unmanage_asset(asset_id: int, session: SessionDep) -> AssetRead:
    """관리 시스템 지정을 해제한다."""
    asset = _get_or_404(session, asset_id)
    asset.managed = False
    session.commit()
    session.refresh(asset)
    return AssetRead.model_validate(asset)


@router.put("/{asset_id}/key", response_model=AssetRead)
def set_key(asset_id: int, payload: KeyIn, session: SessionDep) -> AssetRead:
    """에이전트 Ed25519 공개키를 등록/갱신한다."""
    asset = _get_or_404(session, asset_id)
    asset.public_key = payload.public_key
    session.commit()
    session.refresh(asset)
    return AssetRead.model_validate(asset)


@router.post(
    "/{asset_id}/inventory", response_model=InventoryAck, status_code=status.HTTP_201_CREATED
)
async def ingest_inventory(asset_id: int, request: Request, session: SessionDep) -> InventoryAck:
    """서명된 인벤토리를 수신한다.

    X-Signature 헤더(base64 Ed25519)는 '전송 바디 원본 바이트'에 대한 서명이어야
    하며, 등록된 공개키로 검증에 성공해야만 저장한다.
    """
    asset = _get_or_404(session, asset_id)
    if not asset.public_key:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="no public key registered for asset")

    signature = request.headers.get("X-Signature", "")
    raw = await request.body()
    if not signature or not verify_ed25519(asset.public_key, raw, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid or missing signature")

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


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def deregister_asset(asset_id: int, session: SessionDep) -> None:
    """자산 등록을 삭제한다."""
    asset = _get_or_404(session, asset_id)
    session.delete(asset)
    session.commit()
