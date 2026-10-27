"""KISA Unix 자동 점검 항목(manual→config 전환)의 적재·판정 검증."""

from lejusec.knowledge import load_checks
from lejusec.rules import CheckStatus, evaluate
from lejusec.scanners import Finding

AUTOMATED = {
    "KISA-U-01",
    "KISA-U-05",
    "KISA-U-12",
    "KISA-U-13",
    "KISA-U-16",
    "KISA-U-18",
    "KISA-U-19",
    "KISA-U-21",
    "KISA-U-22",
    "KISA-U-37",
}


def test_kisa_items_are_config_checks() -> None:
    items = {i.id: i for i in load_checks()}
    for cid in AUTOMATED:
        item = items[cid]
        assert item.rule_type == "config", cid
        assert item.tool == "kisa", cid
        assert item.match == cid, cid
        assert not item.is_manual, cid
        # 상세가이드 본문은 유지되어야 한다(점검 기준 상세 표시용).
        assert item.purpose and item.criteria, cid


def test_kisa_remaining_items_stay_manual() -> None:
    items = {i.id: i for i in load_checks()}
    # 전환하지 않은 KISA 항목은 여전히 수동(RAG 전용)이어야 한다.
    assert items["KISA-U-02"].is_manual
    assert items["KISA-U-67"].is_manual


def test_kisa_findings_are_judged() -> None:
    findings = [
        Finding(tool="kisa", check_id="KISA-U-01", passed=True),
        Finding(tool="kisa", check_id="KISA-U-05", passed=False),
    ]
    by_id = {r.check_id: r for r in evaluate(findings)}
    assert by_id["KISA-U-01"].status is CheckStatus.PASS
    assert by_id["KISA-U-05"].status is CheckStatus.FAIL
    # finding이 없는 자동 항목은 비적용(NA).
    assert by_id["KISA-U-16"].status is CheckStatus.NA
    # 전환하지 않은 수동 항목은 결과에 포함되지 않는다.
    assert "KISA-U-02" not in by_id
