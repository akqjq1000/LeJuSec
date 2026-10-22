from lejusec.knowledge import load_checks
from lejusec.rag import search


def test_load_checks_nonempty() -> None:
    checks = load_checks()
    assert len(checks) >= 5
    assert any(c.standard == "KISA" for c in checks)


def test_search_returns_relevant() -> None:
    hits = search("root SSH 원격 접속", k=3)
    assert hits, "expected at least one hit"
    # U-01(root 원격 SSH 접속 제한)이 최상위로 와야 한다.
    assert hits[0].item.id == "U-01"
    assert hits[0].score > 0


def test_search_empty_query() -> None:
    assert search("   ") == []


def test_search_vuln_query() -> None:
    hits = search("취약점 CVE 패치", k=3)
    assert any(h.item.id == "V-01" for h in hits)
