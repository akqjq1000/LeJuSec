"""SQLAlchemy ORM 모델."""

import datetime as dt

from sqlalchemy import Boolean, DateTime, String, func
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
    last_scan_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
