"""API 요청/응답 스키마 (Pydantic)."""

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from lejusec.scanners import Finding


class AssetCreate(BaseModel):
    # hostname은 선택값이다. 비우면 서버가 임시 식별자를 부여하고, 에이전트 첫 통신에서
    # 실제 hostname/주소를 자동으로 채운다(운영자가 직접 입력하지 않아도 됨).
    hostname: str = Field(default="", max_length=255)
    # 네트워크 식별자(IP 또는 도메인). 비우면 에이전트 통신에서 자동 탐지한다.
    address: str = Field(default="", max_length=255)
    # os는 선택값이다. 비우면 에이전트가 보고한 인벤토리에서 자동 탐지해 채운다.
    os: str = Field(default="", max_length=64)
    os_version: str = Field(default="", max_length=64)
    role: str = Field(default="", max_length=64)
    group: str = Field(default="", max_length=64)


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    address: str
    os: str
    os_version: str
    role: str
    group: str
    managed: bool
    agent_status: str
    public_key: str
    last_scan_at: dt.datetime | None
    last_seen_at: dt.datetime | None
    scan_paused: bool
    # 파생 헬스 상태: online | stale | offline | unknown(한 번도 통신 없음)
    health: str = "unknown"
    created_at: dt.datetime

    @classmethod
    def from_asset(cls, asset: object) -> "AssetRead":
        """ORM 자산에서 AssetRead를 만들며 last_seen_at 기준 health를 계산한다."""
        from lejusec.config import settings

        read = cls.model_validate(asset)
        seen = read.last_seen_at
        if seen is None:
            read.health = "unknown"
        else:
            if seen.tzinfo is None:
                seen = seen.replace(tzinfo=dt.UTC)
            age = (dt.datetime.now(dt.UTC) - seen).total_seconds()
            if age <= settings.health_online_seconds:
                read.health = "online"
            elif age <= settings.health_stale_seconds:
                read.health = "stale"
            else:
                read.health = "offline"
        return read


class KeyIn(BaseModel):
    # Ed25519 공개키 (base64, 32바이트 → 44자)
    public_key: str = Field(min_length=1, max_length=128)


class GroupIn(BaseModel):
    # 자산 그룹명. 빈 문자열이면 그룹 해제(미분류).
    group: str = Field(default="", max_length=64)


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class GroupName(BaseModel):
    name: str


class PackageIn(BaseModel):
    name: str
    version: str = ""
    source: str = ""


class ProcessIn(BaseModel):
    pid: int
    name: str = ""
    exe: str = ""


class HostIn(BaseModel):
    """에이전트가 자동 탐지한 호스트 정보(인벤토리에 동봉)."""

    hostname: str = ""
    address: str = ""
    os: str = ""
    os_version: str = ""
    family: str = ""
    arch: str = ""


class InventoryIn(BaseModel):
    host: HostIn | None = None
    packages: list[PackageIn] = Field(default_factory=list)
    processes: list[ProcessIn] = Field(default_factory=list)


class InventoryAck(BaseModel):
    snapshot_id: int
    package_count: int
    process_count: int
    captured_at: dt.datetime


class HeartbeatAck(BaseModel):
    """경량 헬스체크 응답. 에이전트가 살아있음을 서버에 알린다."""

    asset_id: int
    seen_at: dt.datetime


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
    category: str = ""
    # 상세 표시용(점검 기준 항목 클릭 시 전체 내용). 수동 항목은 tool/fix가 비어 있다.
    tool: str = ""
    rule_type: str = ""
    fix: str = ""
    rollback: str = ""
    # KISA 상세가이드 본문(항목 상세)
    purpose: str = ""
    threat: str = ""
    criteria: str = ""
    target: str = ""
    reference: str = ""


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
    apply_status: str


class ApprovedRemediationOut(BaseModel):
    id: int
    check_id: str
    title: str
    script: str
    rollback: str


class ApplyResultIn(BaseModel):
    id: int
    status: str  # applied | rolled_back | failed | skipped
    output: str = ""


class ApplyReportIn(BaseModel):
    results: list[ApplyResultIn] = Field(default_factory=list)


class ApplyReportAck(BaseModel):
    updated: int


class CommandOut(BaseModel):
    """운영자 콘솔용 명령 상태."""

    id: int
    kind: str
    status: str
    result: str
    created_at: dt.datetime
    claimed_at: dt.datetime | None
    done_at: dt.datetime | None


class AgentCommandOut(BaseModel):
    """에이전트 pull 응답(내부 상태 필드는 비노출)."""

    id: int
    kind: str
    params: str


class CommandResultIn(BaseModel):
    id: int
    status: str  # done | failed
    result: str = ""


class CommandReportIn(BaseModel):
    results: list[CommandResultIn] = Field(default_factory=list)


class CommandReportAck(BaseModel):
    updated: int


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
