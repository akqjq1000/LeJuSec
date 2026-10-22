import json

from lejusec.generator import LlmRemediationGenerator, build_generator, generate_remediations
from lejusec.remediation import is_safe


def _ok(_prompt: str) -> str:
    return json.dumps(
        {
            "script": "cp -n /etc/x /etc/x.bak && sed -i s/a/b/ /etc/x",
            "rollback": "cp /etc/x.bak /etc/x",
        }
    )


def _unsafe(_prompt: str) -> str:
    return json.dumps({"script": "rm -rf /", "rollback": "cp /etc/x.bak /etc/x"})


def _broken(_prompt: str) -> str:
    raise RuntimeError("api down")


def test_llm_generates_valid_remediation() -> None:
    gen = LlmRemediationGenerator(_ok)
    rems = gen.generate(["U-01"])
    assert len(rems) == 1
    assert "sed -i" in rems[0].script
    assert is_safe(rems[0].script)


def test_llm_unsafe_output_falls_back_to_template() -> None:
    gen = LlmRemediationGenerator(_unsafe)
    rems = gen.generate(["U-01"])  # U-01은 템플릿 보유
    assert len(rems) == 1
    assert "rm -rf" not in rems[0].script  # LLM 출력 거부
    assert "sshd_config" in rems[0].script  # 템플릿으로 폴백


def test_llm_error_falls_back_to_template() -> None:
    gen = LlmRemediationGenerator(_broken)
    rems = gen.generate(["U-01"])
    assert len(rems) == 1
    assert is_safe(rems[0].script)


def test_llm_no_template_and_unsafe_is_skipped() -> None:
    # V-01은 템플릿 없음 + 위험한 LLM 출력 → 거부되고 폴백도 없어 제외
    gen = LlmRemediationGenerator(_unsafe)
    assert gen.generate(["V-01"]) == []


def test_llm_generates_for_check_without_template() -> None:
    # V-01은 템플릿 없지만 유효한 LLM 출력이면 생성
    gen = LlmRemediationGenerator(_ok)
    rems = gen.generate(["V-01"])
    assert len(rems) == 1
    assert rems[0].check_id == "V-01"


def test_build_generator_defaults_to_template() -> None:
    assert build_generator() is generate_remediations
