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


class ScanResultRow(Base):
    """점검(판정 룰 엔진) 결과 1건. 한 번의 스캔은 동일한 scan_id로 묶인다."""

    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    scan_id: Mapped[str] = mapped_column(String(32), index=True)
    check_id: Mapped[str] = mapped_column(String(64))
    standard: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(8))
    reason: Mapped[str] = mapped_column(String(255))
    evidence: Mapped[str] = mapped_column(Text)  # JSON 배열(finding check_id 목록)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RemediationRow(Base):
    """조치안 1건과 HITL 상태. status: proposed | approved | rejected."""

    __tablename__ = "remediations"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    check_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    script: Mapped[str] = mapped_column(Text)
    rollback: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    static_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    static_notes: Mapped[str] = mapped_column(String(255), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verify_notes: Mapped[str] = mapped_column(String(255), default="")
    # 에이전트 적용 상태: "" | applied | rolled_back | failed | skipped
    apply_status: Mapped[str] = mapped_column(String(16), default="")
    apply_output: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FileBaselineRow(Base):
    """무결성 베이스라인: 경로별 승인된 SHA-256 해시."""

    __tablename__ = "file_baseline"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64))


class IntegrityEventRow(Base):
    """무결성 비교로 탐지된 변경 이벤트."""

    __tablename__ = "integrity_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(512))
    change_type: Mapped[str] = mapped_column(String(16))
    severity: Mapped[str] = mapped_column(String(16))
    detail: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditLogRow(Base):
    """운영자 쓰기 액션 감사 기록."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
