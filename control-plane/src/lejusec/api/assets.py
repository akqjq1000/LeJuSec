"""자산(관리 대상 시스템) CMDB API.

시스템 등록/조회/삭제와 '관리 시스템 지정(manage)·해제(unmanage)'를 제공한다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from lejusec.db import get_session
from lejusec.models import Asset
from lejusec.schemas import AssetCreate, AssetRead

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


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def deregister_asset(asset_id: int, session: SessionDep) -> None:
    """자산 등록을 삭제한다."""
    asset = _get_or_404(session, asset_id)
    session.delete(asset)
    session.commit()
