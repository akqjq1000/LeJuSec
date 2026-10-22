"""파일 무결성 비교(diff) + 부정행위 분류 (결정론적).

중앙 베이스라인과 에이전트 매니페스트를 비교해 변경을 산출하고 경로 기준으로 심각도를
분류한다. 에이전트 자체 해시('agent:self') 변경은 변조로 간주한다(위협 모델 T2).
변경 이벤트의 맥락 판단(정상 패치 vs 공격)은 추후 LLM 보조로 확장 가능하다.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from lejusec.scanners import Severity, severity_rank

AGENT_SELF = "agent:self"

_CRITICAL_PREFIXES = (
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "/etc/ssh/",
    "/boot/",
    "/etc/crontab",
    "/etc/cron",
)


class ChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


class Change(BaseModel):
    path: str
    change_type: ChangeType
    severity: Severity
    detail: str = ""


def classify(path: str, change_type: ChangeType) -> Severity:
    if path == AGENT_SELF:
        return Severity.CRITICAL
    if any(path == p or path.startswith(p) for p in _CRITICAL_PREFIXES):
        return Severity.HIGH
    if change_type is ChangeType.REMOVED:
        return Severity.MEDIUM
    return Severity.LOW


def diff_manifest(baseline: dict[str, str], current: dict[str, str]) -> list[Change]:
    """베이스라인 대비 추가/수정/삭제 변경을 산출한다(심각도 내림차순 정렬)."""
    changes: list[Change] = []
    for path, sha in current.items():
        if path not in baseline:
            changes.append(
                Change(
                    path=path,
                    change_type=ChangeType.ADDED,
                    severity=classify(path, ChangeType.ADDED),
                )
            )
        elif baseline[path] != sha:
            detail = "에이전트 바이너리 변조 의심" if path == AGENT_SELF else ""
            changes.append(
                Change(
                    path=path,
                    change_type=ChangeType.MODIFIED,
                    severity=classify(path, ChangeType.MODIFIED),
                    detail=detail,
                )
            )
    for path in baseline:
        if path not in current:
            changes.append(
                Change(
                    path=path,
                    change_type=ChangeType.REMOVED,
                    severity=classify(path, ChangeType.REMOVED),
                )
            )
    changes.sort(key=lambda c: (-severity_rank(c.severity), c.path))
    return changes
