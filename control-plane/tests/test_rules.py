from lejusec.rules import CheckStatus, evaluate
from lejusec.scanners import Finding, Severity


def _by_id(findings: list[Finding]) -> dict[str, CheckStatus]:
    return {r.check_id: r.status for r in evaluate(findings)}


def test_config_pass_fail_na() -> None:
    findings = [
        Finding(tool="openscap", check_id="rule_sshd_disable_root_login", passed=False),
        Finding(tool="openscap", check_id="rule_set_password_hashing", passed=True),
    ]
    status = _by_id(findings)
    assert status["U-01"] is CheckStatus.FAIL
    assert status["U-02"] is CheckStatus.PASS
    # lynis finding 없음 → U-03/U-04 비적용
    assert status["U-03"] is CheckStatus.NA
    assert status["U-04"] is CheckStatus.NA


def test_vuln_absent_thresholds() -> None:
    assert _by_id([])["V-01"] is CheckStatus.PASS

    high = [Finding(tool="trivy", check_id="CVE-2024-1", severity=Severity.HIGH)]
    results = {r.check_id: r for r in evaluate(high)}
    assert results["V-01"].status is CheckStatus.FAIL
    assert "CVE-2024-1" in results["V-01"].evidence

    low = [Finding(tool="trivy", check_id="CVE-2024-2", severity=Severity.LOW)]
    assert _by_id(low)["V-01"] is CheckStatus.PASS


def test_lynis_config_fail() -> None:
    findings = [Finding(tool="lynis", check_id="SSH-7408", passed=False)]
    assert _by_id(findings)["U-03"] is CheckStatus.FAIL


def test_severity_string_coerced() -> None:
    # 대문자/혼합 severity 문자열도 허용되어야 한다.
    f = Finding(tool="trivy", check_id="CVE-x", severity="HIGH")  # type: ignore[arg-type]
    assert f.severity is Severity.HIGH
