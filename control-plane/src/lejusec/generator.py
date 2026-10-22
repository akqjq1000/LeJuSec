"""조치안 생성기.

기본은 지식베이스 fix/rollback 템플릿(결정론적). `LEJUSEC_GENERATOR_BACKEND="llm"`이고
API 키가 있으면 Claude로 조치 스크립트를 생성하되, 실패하거나 **정적 분석을 통과하지
못하면 템플릿으로 폴백**한다. LLM 출력도 `remediation.static_analysis` 게이트를 반드시
통과해야 하며, 적용 승인은 여전히 HITL이다. 생성기는 `EmbeddingProvider`처럼 교체 가능하다.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from lejusec.config import settings
from lejusec.knowledge import CheckItem, load_checks
from lejusec.remediation import Remediation, static_analysis


def _template_one(item: CheckItem) -> Remediation | None:
    if not item.fix:
        return None
    return Remediation(
        check_id=item.id,
        title=item.title,
        script=item.fix,
        rollback=item.rollback,
        risk=item.severity.value,
    )


def generate_remediations(
    failed_check_ids: list[str],
    checks: tuple[CheckItem, ...] | None = None,
) -> list[Remediation]:
    """템플릿 기반 조치안 생성(기본/폴백). 템플릿 없는 항목은 건너뛴다."""
    items = {c.id: c for c in (checks if checks is not None else load_checks())}
    remediations: list[Remediation] = []
    seen: set[str] = set()
    for check_id in failed_check_ids:
        if check_id in seen:
            continue
        seen.add(check_id)
        item = items.get(check_id)
        if item is not None:
            remediation = _template_one(item)
            if remediation is not None:
                remediations.append(remediation)
    return remediations


def _prompt(item: CheckItem) -> str:
    return (
        "You are a Linux hardening assistant. Produce a SAFE, idempotent remediation for the "
        'security check below. Output ONLY compact JSON: {"script": "...", "rollback": "..."}. '
        "Back up files before editing and provide a working rollback. Never use destructive "
        "commands (rm -rf, dd, mkfs, userdel, reboot, iptables -F, etc.).\n\n"
        f"id: {item.id}\nstandard: {item.standard}\ntitle: {item.title}\n"
        f"tool: {item.tool}\nrationale: {item.rationale}"
    )


class LlmRemediationGenerator:
    """LLM 기반 조치 생성기(교체 가능).

    `complete_fn`은 prompt를 받아 `{"script","rollback"}` JSON 문자열을 돌려주는 호출자.
    각 항목은 LLM 생성 → 정적 분석 통과 시 채택, 실패/위험 시 템플릿으로 폴백한다.
    """

    def __init__(
        self,
        complete_fn: Callable[[str], str],
        checks: tuple[CheckItem, ...] | None = None,
    ) -> None:
        self._complete = complete_fn
        self._checks = checks

    def generate(self, failed_check_ids: list[str]) -> list[Remediation]:
        items = {c.id: c for c in (self._checks if self._checks is not None else load_checks())}
        remediations: list[Remediation] = []
        seen: set[str] = set()
        for check_id in failed_check_ids:
            if check_id in seen:
                continue
            seen.add(check_id)
            item = items.get(check_id)
            if item is None:
                continue
            remediation = self._generate_one(item) or _template_one(item)
            if remediation is not None:
                remediations.append(remediation)
        return remediations

    def _generate_one(self, item: CheckItem) -> Remediation | None:
        try:
            data = json.loads(self._complete(_prompt(item)))
            script = str(data["script"])
            rollback = str(data.get("rollback", ""))
        except Exception:  # noqa: BLE001  (어떤 실패든 템플릿 폴백)
            return None
        if not script.strip() or not rollback.strip():
            return None
        if static_analysis(script):  # 안전하지 않은 LLM 출력은 거부(템플릿 폴백)
            return None
        return Remediation(
            check_id=item.id,
            title=item.title,
            script=script,
            rollback=rollback,
            risk=item.severity.value,
        )


def _anthropic_complete(prompt: str) -> str:
    import anthropic  # 선택 의존성(lazy import)

    client = anthropic.Anthropic(api_key=settings.llm_api_key)
    message = client.messages.create(
        model=settings.llm_model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )


def build_generator() -> Callable[[list[str]], list[Remediation]]:
    """설정에 맞는 조치 생성 함수를 반환한다(기본 템플릿; llm+키면 LLM+폴백)."""
    if settings.generator_backend == "llm" and settings.llm_api_key:
        return LlmRemediationGenerator(_anthropic_complete).generate
    return generate_remediations
