"""결정론적 판정 룰 엔진.

스캐너 finding을 점검 기준(CheckItem)과 대조해 합격/불합격/비적용을 판정한다.
판정은 LLM이 아니라 코드로 수행해 재현성과 감사 적합성을 보장한다(근거는 RAG가 보강).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from lejusec.knowledge import CheckItem, load_checks
from lejusec.scanners import Finding, Severity, severity_rank


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NA = "na"


class CheckResult(BaseModel):
    check_id: str
    standard: str
    title: str
    severity: Severity
    status: CheckStatus
    reason: str
    evidence: list[str]


def _result(item: CheckItem, status: CheckStatus, reason: str, evidence: list[str]) -> CheckResult:
    return CheckResult(
        check_id=item.id,
        standard=item.standard,
        title=item.title,
        severity=item.severity,
        status=status,
        reason=reason,
        evidence=evidence,
    )


def _eval_config(item: CheckItem, findings: list[Finding]) -> CheckResult:
    matches = [f for f in findings if f.tool == item.tool and f.check_id == item.match]
    if not matches:
        return _result(item, CheckStatus.NA, "해당 항목에 대한 수집 결과 없음", [])
    evidence = [f.check_id for f in matches]
    failed = [f for f in matches if f.passed is False]
    if failed:
        return _result(item, CheckStatus.FAIL, f"{len(failed)}건 미준수", evidence)
    if all(f.passed is True for f in matches):
        return _result(item, CheckStatus.PASS, "준수", evidence)
    return _result(item, CheckStatus.NA, "평가 불가(미적용 등)", evidence)


def _eval_vuln_absent(item: CheckItem, findings: list[Finding]) -> CheckResult:
    threshold = severity_rank(item.min_severity or Severity.HIGH)
    hits = [f for f in findings if f.tool == item.tool and severity_rank(f.severity) >= threshold]
    if hits:
        label = (item.min_severity or Severity.HIGH).value
        return _result(
            item,
            CheckStatus.FAIL,
            f"{label} 이상 취약점 {len(hits)}건 발견",
            [f.check_id for f in hits],
        )
    return _result(item, CheckStatus.PASS, "기준 등급 이상 취약점 없음", [])


def evaluate(
    findings: list[Finding],
    checklist: tuple[CheckItem, ...] | None = None,
) -> list[CheckResult]:
    """finding 목록을 점검 기준과 대조해 CheckResult 목록을 반환한다."""
    items = checklist if checklist is not None else load_checks()
    results: list[CheckResult] = []
    for item in items:
        # RAG 전용 지식 항목(수동 점검)은 스캐너 연동이 없어 판정에서 제외한다.
        if item.is_manual:
            continue
        if item.rule_type == "vuln_absent":
            results.append(_eval_vuln_absent(item, findings))
        else:
            results.append(_eval_config(item, findings))
    return results
