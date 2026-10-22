from lejusec.scanners import (
    Severity,
    parse_lynis_report,
    parse_openscap_xccdf,
    parse_trivy_json,
    select_tools,
    severity_rank,
)

TRIVY = """
{"Results":[{"Target":"app","Vulnerabilities":[
  {"VulnerabilityID":"CVE-2024-0001","PkgName":"openssl","Severity":"HIGH","Title":"openssl flaw"},
  {"VulnerabilityID":"CVE-2024-0002","PkgName":"zlib","Severity":"CRITICAL"}
]}]}
"""

LYNIS = """
# lynis report
warning[]=SSH-7408|Consider hardening SSH configuration|-|-
suggestion[]=AUTH-9286|Set password aging policy|-|-
hardening_index=60
"""

OPENSCAP = """
<TestResult xmlns="http://checklists.nist.gov/xccdf/1.2">
  <rule-result idref="rule_sshd_disable_root_login"><result>fail</result></rule-result>
  <rule-result idref="rule_set_password_hashing"><result>pass</result></rule-result>
  <rule-result idref="rule_na"><result>notapplicable</result></rule-result>
</TestResult>
"""


def test_parse_trivy() -> None:
    findings = parse_trivy_json(TRIVY)
    assert len(findings) == 2
    assert findings[0].tool == "trivy"
    assert findings[0].check_id == "CVE-2024-0001"
    assert findings[0].severity is Severity.HIGH
    assert findings[0].passed is None
    assert findings[1].severity is Severity.CRITICAL


def test_parse_lynis() -> None:
    findings = parse_lynis_report(LYNIS)
    assert len(findings) == 2
    warn = findings[0]
    assert warn.check_id == "SSH-7408"
    assert warn.severity is Severity.HIGH
    assert warn.passed is False
    assert findings[1].check_id == "AUTH-9286"
    assert findings[1].severity is Severity.LOW


def test_parse_openscap() -> None:
    findings = parse_openscap_xccdf(OPENSCAP)
    by_id = {f.check_id: f for f in findings}
    assert by_id["rule_sshd_disable_root_login"].passed is False
    assert by_id["rule_set_password_hashing"].passed is True
    assert by_id["rule_na"].passed is None


def test_select_tools_allowlist() -> None:
    assert select_tools("linux") == ["openscap", "lynis", "trivy"]
    assert select_tools("container") == ["trivy"]
    assert select_tools("unknown-kind") == []


def test_severity_rank_order() -> None:
    assert severity_rank(Severity.CRITICAL) > severity_rank(Severity.HIGH)
    assert severity_rank(Severity.HIGH) > severity_rank(Severity.LOW)
