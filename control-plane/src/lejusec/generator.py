"""조치안 생성기 (지식베이스 템플릿 기반, 결정론적).

점검 기준(CheckItem)의 fix/rollback 템플릿으로 조치안을 생성한다. LLM 기반 생성기로
교체 가능한 자리이며, 기본은 재현 가능한 템플릿 생성이다. 생성 결과는 반드시
remediation.static_analysis를 통과해야 승인될 수 있다.
"""

from __future__ import annotations

from lejusec.knowledge import CheckItem, load_checks
from lejusec.remediation import Remediation


def generate_remediations(
    failed_check_ids: list[str],
    checks: tuple[CheckItem, ...] | None = None,
) -> list[Remediation]:
    """불합격 점검 항목 id 목록에 대해 조치안을 생성한다(템플릿 없는 항목은 건너뜀)."""
    items = {c.id: c for c in (checks if checks is not None else load_checks())}
    remediations: list[Remediation] = []
    seen: set[str] = set()
    for check_id in failed_check_ids:
        if check_id in seen:
            continue
        seen.add(check_id)
        item = items.get(check_id)
        if item is None or not item.fix:
            continue
        remediations.append(
            Remediation(
                check_id=item.id,
                title=item.title,
                script=item.fix,
                rollback=item.rollback,
                risk=item.severity.value,
            )
        )
    return remediations
