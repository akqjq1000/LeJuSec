"""자산 그룹 레지스트리 API.

그룹명을 별도 테이블에 저장해 '자산이 없는 빈 그룹'도 유지한다. 목록은 레지스트리
그룹명과 자산에 실제로 지정된 그룹명의 합집합을 반환한다(레거시 호환).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from lejusec.auth import get_actor, record_audit
from lejusec.db import get_session
from lejusec.models import Asset, AssetGroupRow
from lejusec.schemas import GroupCreate, GroupName

router = APIRouter(prefix="/asset-groups", tags=["groups"])

SessionDep = Annotated[Session, Depends(get_session)]
Actor = Annotated[str, Depends(get_actor)]


def _all_group_names(session: Session) -> list[str]:
    registry = set(session.scalars(select(AssetGroupRow.name)).all())
    used = set(session.scalars(select(Asset.group).where(Asset.group != "")).all())
    return sorted(registry | used)


@router.get("", response_model=list[str])
def list_groups(session: SessionDep) -> list[str]:
    """그룹명 목록(레지스트리 ∪ 자산에 지정된 그룹)."""
    return _all_group_names(session)


@router.post("", response_model=GroupName, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, session: SessionDep, actor: Actor) -> GroupName:
    """새 자산 그룹을 등록한다(자산 없이도 유지)."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="group name required")
    if name in _all_group_names(session):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="group already exists")
    session.add(AssetGroupRow(name=name))
    record_audit(session, actor, "group.create", name)
    session.commit()
    return GroupName(name=name)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(name: str, session: SessionDep, actor: Actor) -> None:
    """그룹을 삭제한다. 해당 그룹의 자산은 미분류로 되돌린다."""
    session.execute(update(Asset).where(Asset.group == name).values(group=""))
    row = session.scalar(select(AssetGroupRow).where(AssetGroupRow.name == name))
    if row is not None:
        session.delete(row)
    record_audit(session, actor, "group.delete", name)
    session.commit()
