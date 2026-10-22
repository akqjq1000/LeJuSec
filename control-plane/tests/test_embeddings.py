from lejusec.embeddings import HashingEmbedding, cosine
from lejusec.rag import embedding_search, retrieve


def test_hashing_deterministic_and_normalized() -> None:
    embedder = HashingEmbedding()
    v1 = embedder.embed("root ssh 원격 접속")
    v2 = embedder.embed("root ssh 원격 접속")
    assert v1 == v2  # 결정론적
    assert len(v1) == 256
    assert abs(cosine(v1, v1) - 1.0) < 1e-9  # L2 정규화 → 자기 코사인 1
    # 무관한 텍스트는 유사도가 낮다
    assert cosine(v1, embedder.embed("완전히 다른 내용 xyzzy")) < 0.5


def test_embedding_search_relevance() -> None:
    hits = embedding_search("root SSH 원격 접속 제한", k=5)
    assert hits
    assert hits[0].score > 0
    assert "U-01" in [h.item.id for h in hits]


def test_embedding_search_vuln() -> None:
    hits = embedding_search("알려진 취약점 CVE 패치", k=5)
    assert any(h.item.id == "V-01" for h in hits)


def test_retrieve_default_is_embedding() -> None:
    hits = retrieve("패스워드 해시 알고리즘", k=3)
    assert hits
    assert any(h.item.id == "U-02" for h in hits)


def test_embedding_empty_query() -> None:
    assert embedding_search("   ") == []
