"""샌드박스 검증 (교체 가능 백엔드).

- dry-run(기본): 실제 실행 없이 정적 분석 재확인 + 롤백 존재 확인. 오프라인·결정론.
- container: 격리된 Docker 컨테이너(`--network=none`)에서 조치 스크립트를 적용해
  오류 없이 수행되는지 확인. Docker 미설치 시 안전하게 실패를 반환한다.

어느 백엔드든 조치는 먼저 정적 분석을 통과해야 하며, 승인은 여전히 HITL이다.
"""

from __future__ import annotations

import shutil
import subprocess

from pydantic import BaseModel

from lejusec.config import settings
from lejusec.remediation import Remediation, static_analysis


class SandboxResult(BaseModel):
    ok: bool
    notes: str
    sandbox: str = "dry-run"


def _static_block(remediation: Remediation, sandbox: str) -> SandboxResult | None:
    violations = static_analysis(remediation.script)
    if violations:
        reasons = "; ".join(v.reason for v in violations)
        return SandboxResult(
            ok=False, notes=f"정적 분석 위반 {len(violations)}건: {reasons}", sandbox=sandbox
        )
    if not remediation.rollback.strip():
        return SandboxResult(ok=False, notes="롤백 스크립트가 없어 검증 불가", sandbox=sandbox)
    return None


def _dry_run(remediation: Remediation) -> SandboxResult:
    blocked = _static_block(remediation, "dry-run")
    if blocked is not None:
        return blocked
    return SandboxResult(
        ok=True,
        notes="정적 분석 통과, 롤백 존재 (컨테이너 샌드박스 미연결: dry-run)",
        sandbox="dry-run",
    )


def container_command(image: str, script: str) -> list[str]:
    """격리 컨테이너에서 스크립트를 실행하는 docker 명령(네트워크 차단·자원 제한)."""
    return [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--memory=256m",
        "--pids-limit=256",
        image,
        "bash",
        "-c",
        script,
    ]


def _container(remediation: Remediation) -> SandboxResult:
    blocked = _static_block(remediation, "container")
    if blocked is not None:
        return blocked
    if shutil.which("docker") is None:
        return SandboxResult(
            ok=False, notes="docker 미설치: 컨테이너 샌드박스 사용 불가", sandbox="container"
        )
    try:
        proc = subprocess.run(
            container_command(settings.sandbox_image, remediation.script),
            capture_output=True,
            text=True,
            timeout=settings.sandbox_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(ok=False, notes="샌드박스 타임아웃", sandbox="container")
    if proc.returncode == 0:
        return SandboxResult(ok=True, notes="컨테이너 적용 성공 (exit 0)", sandbox="container")
    detail = (proc.stderr or proc.stdout).strip().replace("\n", " ")[:200]
    return SandboxResult(
        ok=False,
        notes=f"컨테이너 적용 실패 (exit {proc.returncode}): {detail}",
        sandbox="container",
    )


def verify(remediation: Remediation) -> SandboxResult:
    """설정된 백엔드로 조치안을 검증한다(기본 dry-run)."""
    if settings.sandbox_backend == "container":
        return _container(remediation)
    return _dry_run(remediation)
