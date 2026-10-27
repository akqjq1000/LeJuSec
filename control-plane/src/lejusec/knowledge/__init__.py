"""점검 기준 지식베이스 (RAG 코퍼스 + 룰 엔진 입력).

각 항목은 점검 기준(제목·근거)과 (가능하면) 매칭 규칙을 담는다.
RAG(rag.py)는 title/rationale로 근거를 검색하고, 룰 엔진(rules.py)은 tool/match로
스캐너 finding과 대조해 합격/불합격을 판정한다.

코퍼스는 두 파일을 병합한다:
- ``checks.json``   — 스캐너와 연동되는 자동 판정 점검(rule_type: config | vuln_absent)
- ``kisa_unix.json`` — KISA『주요정보통신기반시설 기술적 취약점 분석·평가 방법 상세가이드』
  Unix 부분(U-01~U-67)을 RAG 근거로 등록한 지식 항목(rule_type: manual)

id가 겹치면 자동 판정 점검(checks.json)을 우선한다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from pydantic import BaseModel

from lejusec.scanners import Severity

# RAG 전용(수동 점검) 지식 항목을 나타내는 rule_type. 룰 엔진은 이 항목을 판정에서 제외한다.
MANUAL_RULE_TYPE = "manual"

# 병합 대상 코퍼스 파일(순서대로 로드하며, 먼저 등록된 id가 우선한다).
_CORPUS_FILES = ("checks.json", "kisa_unix.json")


class CheckItem(BaseModel):
    id: str
    standard: str
    title: str
    severity: Severity
    rationale: str
    # 점검 분류(예: "계정 관리"). 지식 항목의 분류 표시용. 자동 점검은 비워둘 수 있다.
    category: str = ""
    # KISA 상세가이드 본문 구성(항목 상세 표시용). 자동 점검은 비워둘 수 있다.
    purpose: str = ""  # 점검 목적
    threat: str = ""  # 보안 위협
    criteria: str = ""  # 판단 기준(양호/취약)
    target: str = ""  # 점검 대상(적용 플랫폼)
    reference: str = ""  # 참고
    # 연동 스캐너(openscap | lynis | trivy …). RAG 전용 수동 항목은 비운다.
    tool: str = ""
    rule_type: str = MANUAL_RULE_TYPE  # "config" | "vuln_absent" | "manual"
    match: str | None = None
    min_severity: Severity | None = None
    # 조치안 템플릿(있을 때). 자동 조치가 어려우면 비워 두고 수동 조치로 처리한다.
    fix: str = ""
    rollback: str = ""

    @property
    def is_manual(self) -> bool:
        """스캐너 연동 없이 RAG 근거로만 쓰이는 수동 점검 항목인지."""
        return self.rule_type == MANUAL_RULE_TYPE


@lru_cache
def load_checks() -> tuple[CheckItem, ...]:
    """번들된 코퍼스 파일들을 병합해 CheckItem 튜플로 로드한다(캐시).

    checks.json(자동 판정)을 먼저 싣고 kisa_unix.json(KISA Unix 지식)을 덧붙이되,
    id가 중복되면 먼저 등록된 자동 판정 항목을 유지한다.
    """
    merged: dict[str, CheckItem] = {}
    for filename in _CORPUS_FILES:
        resource = resources.files(__package__).joinpath(filename)
        if not resource.is_file():
            continue
        for raw_item in json.loads(resource.read_text(encoding="utf-8")):
            item = CheckItem.model_validate(raw_item)
            merged.setdefault(item.id, item)
    return tuple(merged.values())
