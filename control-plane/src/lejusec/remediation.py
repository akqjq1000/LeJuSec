"""조치안 모델 + 정적 분석(파괴적/비가역 명령 차단).

위협 모델 T4(위험한 자동 조치) 대응의 핵심 안전장치. LLM/템플릿이 생성한 조치
스크립트는 반드시 이 정적 분석을 통과해야 하며, 위반이 있으면 승인(approve)이
차단된다(HITL 게이트).
"""

from __future__ import annotations

import re

from pydantic import BaseModel


class Remediation(BaseModel):
    check_id: str
    title: str
    script: str
    rollback: str = ""
    risk: str = ""


class Violation(BaseModel):
    rule: str
    reason: str
    line: str


# (rule 이름, 정규식, 사유) — 파괴적/비가역/위험 패턴 거부 목록(denylist).
_RULES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "rm_recursive_force",
        re.compile(
            r"\brm\b[^\n]*-[a-zA-Z]*r[a-zA-Z]*f"
            r"|\brm\b[^\n]*-[a-zA-Z]*f[a-zA-Z]*r"
            r"|\brm\b[^\n]*(-r\b[^\n]*-f\b|-f\b[^\n]*-r\b)"
        ),
        "재귀 강제 삭제(rm -rf)",
    ),
    ("dd_to_device", re.compile(r"\bdd\b[^\n]*of=/dev/"), "블록 디바이스 덮어쓰기(dd of=/dev/..)"),
    ("mkfs", re.compile(r"\bmkfs(\.\w+)?\b"), "파일시스템 포맷(mkfs)"),
    ("overwrite_device", re.compile(r">\s*/dev/(sd|nvme|vd|hd)"), "디바이스로 리다이렉트"),
    ("fork_bomb", re.compile(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"), "포크 폭탄"),
    (
        "pipe_to_shell",
        re.compile(r"\b(curl|wget)\b[^\n]*\|\s*(sudo\s+)?(ba)?sh\b"),
        "원격 스크립트 파이프 실행(curl|sh)",
    ),
    (
        "recursive_perm_root",
        re.compile(r"\b(chmod|chown)\b[^\n]*-[a-zA-Z]*R[^\n]*\s/(\s|$)"),
        "루트에 재귀 권한/소유권 변경",
    ),
    ("chmod_777_root", re.compile(r"\bchmod\b[^\n]*\b777\b[^\n]*\s/(\s|$)"), "루트 777 권한"),
    ("account_delete", re.compile(r"\b(userdel|deluser)\b"), "계정 삭제"),
    (
        "power_control",
        re.compile(r"\b(shutdown|reboot|halt|poweroff)\b|\binit\s+0\b"),
        "전원/재부팅 제어",
    ),
    (
        "overwrite_critical",
        re.compile(r">\s*/etc/(passwd|shadow|sudoers)\b"),
        "핵심 시스템 파일 덮어쓰기",
    ),
    ("firewall_flush", re.compile(r"\biptables\b[^\n]*\s-F\b"), "방화벽 규칙 전체 삭제"),
    ("mass_kill", re.compile(r"\bkill\b[^\n]*-9[^\n]*\s-1\b"), "전체 프로세스 강제 종료"),
]


def static_analysis(script: str) -> list[Violation]:
    """스크립트에서 위험 패턴을 찾아 위반 목록을 반환한다(빈 목록이면 안전)."""
    violations: list[Violation] = []
    for raw_line in script.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        for name, pattern, reason in _RULES:
            if pattern.search(line):
                violations.append(Violation(rule=name, reason=reason, line=line))
    return violations


def is_safe(script: str) -> bool:
    return not static_analysis(script)
