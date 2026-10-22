"""API 요청/응답 스키마 (Pydantic)."""

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from lejusec.scanners import Finding


class AssetCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    os: str = Field(min_length=1, max_length=64)
    os_version: str = Field(default="", max_length=64)
    role: str = Field(default="", max_length=64)


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    os: str
    os_version: str
    role: str
    managed: bool
    agent_status: str
    public_key: str
    last_scan_at: dt.datetime | None
    created_at: dt.datetime


class KeyIn(BaseModel):
    # Ed25519 공개키 (base64, 32바이트 → 44자)
    public_key: str = Field(min_length=1, max_length=128)


class PackageIn(BaseModel):
    name: str
    version: str = ""
    source: str = ""


class ProcessIn(BaseModel):
    pid: int
    name: str = ""
    exe: str = ""


class InventoryIn(BaseModel):
    packages: list[PackageIn] = Field(default_factory=list)
    processes: list[ProcessIn] = Field(default_factory=list)


class InventoryAck(BaseModel):
    snapshot_id: int
    package_count: int
    process_count: int
    captured_at: dt.datetime


class ScanIn(BaseModel):
    findings: list[Finding] = Field(default_factory=list)


class ScanAck(BaseModel):
    scan_id: str
    total: int
    passed: int
    failed: int
    na: int


class CheckResultOut(BaseModel):
    check_id: str
    standard: str
    title: str
    severity: str
    status: str
    reason: str
    evidence: list[str]


class CheckItemOut(BaseModel):
    id: str
    standard: str
    title: str
    severity: str
    rationale: str


class CheckSearchHit(BaseModel):
    item: CheckItemOut
    score: float


class RemediationOut(BaseModel):
    id: int
    check_id: str
    title: str
    script: str
    rollback: str
    status: str
    static_ok: bool
    static_notes: str
    verified: bool
    verify_notes: str


class GenerateAck(BaseModel):
    generated: int
    proposed: list[RemediationOut]


class VerifyOut(BaseModel):
    ok: bool
    notes: str
    sandbox: str


class FileEntryIn(BaseModel):
    path: str
    sha256: str
    size: int = 0
    mode: str = ""


class IntegrityIn(BaseModel):
    agent_sha256: str = ""
    files: list[FileEntryIn] = Field(default_factory=list)


class IntegrityAck(BaseModel):
    baseline_established: bool
    baseline_files: int
    changes: int
    critical: int
    high: int


class IntegrityEventOut(BaseModel):
    path: str
    change_type: str
    severity: str
    detail: str
    created_at: dt.datetime


class BaselineSummary(BaseModel):
    files: int
    has_agent_hash: bool


class AuditOut(BaseModel):
    actor: str
    action: str
    target: str
    created_at: dt.datetime


class InventorySummaryOut(BaseModel):
    package_count: int
    process_count: int
    captured_at: dt.datetime | None


class SummaryOut(BaseModel):
    assets_total: int
    assets_managed: int
    checks_pass: int
    checks_fail: int
    checks_na: int
    remediations_open: int
    integrity_high_critical: int
