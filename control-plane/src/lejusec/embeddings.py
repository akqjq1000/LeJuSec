"""임베딩 공급자(교체 가능) + 오프라인 결정론 기본 구현.

`HashingEmbedding`은 feature hashing(해싱 트릭)으로 텍스트를 고정 차원 벡터로 만든다.
외부 모델·네트워크 없이 결정론적이라 CI에서 완전 검증되며, 추후 sentence-transformers
나 API 기반 `EmbeddingProvider`로 교체해도 코사인 검색 로직은 동일하다.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

_TOKEN = re.compile(r"[0-9a-z가-힣]+")


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class HashingEmbedding:
    """해싱 트릭 기반 결정론적 벡터라이저(부호 해싱 + L2 정규화)."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            idx = value % self.dim
            sign = 1.0 if (value >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec


def cosine(a: list[float], b: list[float]) -> float:
    """정규화 벡터 간 코사인 유사도(= 내적)."""
    return sum(x * y for x, y in zip(a, b, strict=False))
