"""RAG 근거 검색 (어휘 기반).

점검 기준 코퍼스(knowledge.checks)에 대해 쿼리 토큰 겹침으로 관련 근거를 검색한다.
외부 임베딩 모델 의존 없이 결정론적이며, 추후 벡터 임베딩 retriever로 교체할 수 있다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lejusec.knowledge import CheckItem, load_checks

_TOKEN = re.compile(r"[0-9a-z가-힣]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


@dataclass
class Hit:
    item: CheckItem
    score: float


def search(query: str, k: int = 5, checks: tuple[CheckItem, ...] | None = None) -> list[Hit]:
    """쿼리와 관련된 점검 기준을 점수 순으로 최대 k개 반환한다."""
    items = checks if checks is not None else load_checks()
    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    hits: list[Hit] = []
    for item in items:
        doc = _tokens(f"{item.title} {item.rationale} {item.standard} {item.id}")
        overlap = len(query_tokens & doc)
        if overlap:
            hits.append(Hit(item=item, score=overlap / len(query_tokens)))
    hits.sort(key=lambda h: (h.score, h.item.id), reverse=True)
    return hits[:k]
