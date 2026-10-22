from lejusec.generator import generate_remediations
from lejusec.remediation import is_safe


def test_generate_known() -> None:
    rems = generate_remediations(["U-01", "U-04"])
    assert {r.check_id for r in rems} == {"U-01", "U-04"}
    for rem in rems:
        assert rem.script and rem.rollback
        # 템플릿 조치는 정적 분석을 통과해야 한다.
        assert is_safe(rem.script), f"template not safe: {rem.check_id}"


def test_generate_skips_no_template_and_unknown() -> None:
    # V-01은 자동 조치 템플릿 없음(수동), ZZZ-99는 존재하지 않음.
    assert generate_remediations(["V-01", "ZZZ-99"]) == []


def test_generate_dedup() -> None:
    assert len(generate_remediations(["U-01", "U-01"])) == 1
