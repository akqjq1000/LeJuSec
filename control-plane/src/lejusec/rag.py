"""RAG 근거 검색.

점검 기준 코퍼스(knowledge.checks)에 대해 관련 근거를 검색한다. 두 백엔드를 제공한다:
- embedding(기본): 해싱 임베딩 벡터의 코사인 유사도
- lexical: 쿼리 토큰 겹침
둘 다 외부 모델 의존이 없어 결정론적이며, 임베딩 공급자는 교체 가능하다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lejusec.config import settings
from lejusec.embeddings import EmbeddingProvider, HashingEmbedding, cosine
from lejusec.knowledge import CheckItem, load_checks

_TOKEN = re.compile(r"[0-9a-z가-힣]+")
_default_provider: EmbeddingProvider = HashingEmbedding()


def _doc_text(item: CheckItem) -> str:
    return f"{item.title} {item.rationale} {item.standard} {item.id}"


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


def embedding_search(
    query: str,
    k: int = 5,
    checks: tuple[CheckItem, ...] | None = None,
    provider: EmbeddingProvider | None = None,
) -> list[Hit]:
    """임베딩 코사인 유사도로 관련 점검 기준을 점수 순으로 반환한다."""
    if not query.strip():
        return []
    items = checks if checks is not None else load_checks()
    embedder = provider or _default_provider
    query_vec = embedder.embed(query)
    hits: list[Hit] = []
    for item in items:
        score = cosine(query_vec, embedder.embed(_doc_text(item)))
        if score > 0.0:
            hits.append(Hit(item=item, score=score))
    hits.sort(key=lambda h: (h.score, h.item.id), reverse=True)
    return hits[:k]


def retrieve(query: str, k: int = 5, checks: tuple[CheckItem, ...] | None = None) -> list[Hit]:
    """설정된 백엔드로 근거를 검색한다(기본 embedding)."""
    if settings.rag_backend == "lexical":
        return search(query, k, checks)
    return embedding_search(query, k, checks)
