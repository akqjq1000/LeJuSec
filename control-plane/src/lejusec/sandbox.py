"""샌드박스 검증 (드라이런 기본 구현).

운영 반영 전, 격리 환경에서 조치를 적용하고 재점검하는 자리. 기본 구현은 실제 실행
없이 정적 분석 재확인과 롤백 존재 확인만 수행한다(dry-run). 컨테이너/VM 기반 실행
러너로 교체할 수 있다.
"""

from __future__ import annotations

from pydantic import BaseModel

from lejusec.remediation import Remediation, static_analysis


class SandboxResult(BaseModel):
    ok: bool
    notes: str
    sandbox: str = "dry-run"


def verify(remediation: Remediation) -> SandboxResult:
    """조치안을 드라이런 검증한다(실제 실행 아님)."""
    violations = static_analysis(remediation.script)
    if violations:
        reasons = "; ".join(v.reason for v in violations)
        return SandboxResult(ok=False, notes=f"정적 분석 위반 {len(violations)}건: {reasons}")
    if not remediation.rollback.strip():
        return SandboxResult(ok=False, notes="롤백 스크립트가 없어 검증 불가")
    return SandboxResult(
        ok=True,
        notes="정적 분석 통과, 롤백 존재 (컨테이너 샌드박스 미연결: dry-run)",
    )
