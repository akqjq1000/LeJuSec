"""점검 기준 지식베이스 (RAG 코퍼스 + 룰 엔진 입력).

checks.json의 각 항목은 점검 기준(제목·근거)과 매칭 규칙을 함께 담는다.
RAG(rag.py)는 title/rationale로 근거를 검색하고, 룰 엔진(rules.py)은 tool/match로
스캐너 finding과 대조해 합격/불합격을 판정한다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from pydantic import BaseModel

from lejusec.scanners import Severity


class CheckItem(BaseModel):
    id: str
    standard: str
    title: str
    severity: Severity
    rationale: str
    tool: str
    rule_type: str  # "config" | "vuln_absent"
    match: str | None = None
    min_severity: Severity | None = None


@lru_cache
def load_checks() -> tuple[CheckItem, ...]:
    """패키지에 번들된 checks.json을 CheckItem 튜플로 로드한다(캐시)."""
    raw = resources.files(__package__).joinpath("checks.json").read_text(encoding="utf-8")
    items = json.loads(raw)
    return tuple(CheckItem.model_validate(item) for item in items)
