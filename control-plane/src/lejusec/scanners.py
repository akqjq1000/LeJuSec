"""점검 도구 래핑.

각 스캐너(Trivy/Lynis/OpenSCAP) 출력을 정규화된 `Finding`으로 변환한다.
`parse_*(raw)` 는 순수 함수(테스트 대상)이고, `run_trivy_fs` 는 도구가 설치돼
있으면 실행 후 parse 한다. 결정론 우선 원칙에 따라 합격/불합격 판정은
`rules.evaluate` 가 담당하며, 여기서는 '사실(finding)'만 수집한다.

OpenSCAP 결과(XCCDF XML)는 로컬 신뢰 도구의 출력이지만, 방어적으로 defusedxml로
파싱해 XXE/엔티티 폭탄을 차단한다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from enum import StrEnum

from defusedxml.ElementTree import fromstring as safe_xml_fromstring
from pydantic import BaseModel, field_validator


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.UNKNOWN: 0,
    Severity.INFO: 1,
    Severity.LOW: 2,
    Severity.MEDIUM: 3,
    Severity.HIGH: 4,
    Severity.CRITICAL: 5,
}


def severity_rank(severity: Severity) -> int:
    return _SEVERITY_RANK[severity]


def coerce_severity(value: str) -> Severity:
    try:
        return Severity(value.strip().lower())
    except ValueError:
        return Severity.UNKNOWN


class Finding(BaseModel):
    tool: str
    check_id: str
    title: str = ""
    severity: Severity = Severity.UNKNOWN
    # config 점검 결과(pass/fail). 취약점 존재형(Trivy)은 None(존재 자체가 이슈).
    passed: bool | None = None
    target: str = ""
    detail: str = ""

    @field_validator("severity", mode="before")
    @classmethod
    def _coerce_severity_field(cls, value: object) -> object:
        if isinstance(value, str):
            return coerce_severity(value)
        return value


def parse_trivy_json(raw: str) -> list[Finding]:
    """Trivy JSON(`trivy ... -f json`)의 취약점을 Finding으로 변환."""
    data = json.loads(raw)
    findings: list[Finding] = []
    for result in data.get("Results", []):
        target = str(result.get("Target", ""))
        for vuln in result.get("Vulnerabilities") or []:
            findings.append(
                Finding(
                    tool="trivy",
                    check_id=str(vuln.get("VulnerabilityID", "")),
                    title=str(vuln.get("Title") or vuln.get("PkgName") or ""),
                    severity=coerce_severity(str(vuln.get("Severity", "unknown"))),
                    passed=None,
                    target=target,
                    detail=str(vuln.get("PkgName", "")),
                )
            )
    return findings


def parse_lynis_report(raw: str) -> list[Finding]:
    """Lynis 리포트(.dat)의 warning[]/suggestion[] 항목을 Finding으로 변환."""
    findings: list[Finding] = []
    kinds = (("warning[]=", Severity.HIGH), ("suggestion[]=", Severity.LOW))
    for raw_line in raw.splitlines():
        text = raw_line.strip()
        for prefix, severity in kinds:
            if text.startswith(prefix):
                payload = text[len(prefix) :]
                parts = payload.split("|")
                findings.append(
                    Finding(
                        tool="lynis",
                        check_id=parts[0] if parts and parts[0] else "unknown",
                        title=parts[1] if len(parts) > 1 else "",
                        severity=severity,
                        passed=False,
                        detail=payload,
                    )
                )
    return findings


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_openscap_xccdf(raw: str) -> list[Finding]:
    """OpenSCAP XCCDF 결과 XML의 rule-result/result를 Finding으로 변환."""
    root = safe_xml_fromstring(raw)
    findings: list[Finding] = []
    for elem in root.iter():
        if _local_name(elem.tag) != "rule-result":
            continue
        idref = elem.get("idref", "")
        result_text = ""
        for child in elem:
            if _local_name(child.tag) == "result":
                result_text = (child.text or "").strip().lower()
                break
        if not result_text:
            continue
        # pass/fail 외(notapplicable 등)는 평가 대상 아님 → passed=None
        passed: bool | None
        if result_text == "pass":
            passed = True
        elif result_text == "fail":
            passed = False
        else:
            passed = None
        findings.append(
            Finding(
                tool="openscap",
                check_id=idref,
                title=idref,
                severity=Severity.MEDIUM,
                passed=passed,
                detail=result_text,
            )
        )
    return findings


PARSERS: dict[str, Callable[[str], list[Finding]]] = {
    "trivy": parse_trivy_json,
    "lynis": parse_lynis_report,
    "openscap": parse_openscap_xccdf,
}

# 대상 유형별 허용 점검 도구(allowlist) — 오케스트레이터 라우팅의 결정론적 기반.
_TOOLS_BY_TARGET: dict[str, list[str]] = {
    "linux": ["openscap", "lynis", "trivy"],
    "container": ["trivy"],
    "image": ["trivy"],
}


def select_tools(target_kind: str) -> list[str]:
    """대상 유형에 맞는 허용된 점검 도구 목록을 반환한다(없으면 빈 목록)."""
    return list(_TOOLS_BY_TARGET.get(target_kind, []))


def run_trivy_fs(path: str, timeout: int = 600) -> list[Finding]:
    """trivy가 설치돼 있으면 파일시스템 스캔을 실행하고 결과를 parse 한다."""
    if shutil.which("trivy") is None:
        return []
    proc = subprocess.run(  # noqa: S603  (고정 인자, shell 미사용)
        ["trivy", "fs", "--quiet", "--format", "json", path],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    return parse_trivy_json(proc.stdout) if proc.stdout.strip() else []
