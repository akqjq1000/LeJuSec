"""SQLAlchemy ORM 모델."""

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Asset(Base):
    """관리 대상 시스템 (자산 CMDB의 단위)."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    os: Mapped[str] = mapped_column(String(64))
    os_version: Mapped[str] = mapped_column(String(64), default="")
    role: Mapped[str] = mapped_column(String(64), default="")
    # managed: 관리 시스템 지정(True)/해제(False)
    managed: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_status: Mapped[str] = mapped_column(String(32), default="unknown")
    # 에이전트 Ed25519 공개키(base64). 인벤토리 서명 검증에 사용.
    public_key: Mapped[str] = mapped_column(String(128), default="")
    last_scan_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InventorySnapshot(Base):
    """에이전트가 전송한 인벤토리 스냅샷 (서명 검증 후 저장)."""

    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    captured_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    package_count: Mapped[int] = mapped_column(Integer, default=0)
    process_count: Mapped[int] = mapped_column(Integer, default=0)
    # 서명이 검증된 원본 JSON 페이로드(증적).
    payload: Mapped[str] = mapped_column(Text)
