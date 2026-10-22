from lejusec.remediation import Remediation
from lejusec.sandbox import verify


def test_verify_ok() -> None:
    rem = Remediation(check_id="U-01", title="t", script="sed -i 's/a/b/' f", rollback="cp f.bak f")
    result = verify(rem)
    assert result.ok is True
    assert result.sandbox == "dry-run"


def test_verify_unsafe_script() -> None:
    rem = Remediation(check_id="x", title="t", script="rm -rf /", rollback="cp f.bak f")
    assert verify(rem).ok is False


def test_verify_requires_rollback() -> None:
    rem = Remediation(check_id="x", title="t", script="sed -i 's/a/b/' f", rollback="")
    assert verify(rem).ok is False
