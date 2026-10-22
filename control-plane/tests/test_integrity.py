from lejusec.integrity import AGENT_SELF, ChangeType, classify, diff_manifest
from lejusec.scanners import Severity


def test_diff_added_modified_unchanged() -> None:
    base = {"/etc/motd": "a", "/etc/hosts": "b", AGENT_SELF: "x"}
    current = {"/etc/motd": "a", "/etc/hosts": "B", "/opt/new": "c", AGENT_SELF: "x"}
    by_path = {c.path: c for c in diff_manifest(base, current)}
    assert by_path["/etc/hosts"].change_type is ChangeType.MODIFIED
    assert by_path["/opt/new"].change_type is ChangeType.ADDED
    assert "/etc/motd" not in by_path  # 변경 없음
    assert AGENT_SELF not in by_path


def test_diff_removed_medium() -> None:
    changes = diff_manifest({"/etc/x": "1"}, {})
    assert len(changes) == 1
    assert changes[0].change_type is ChangeType.REMOVED
    assert changes[0].severity is Severity.MEDIUM


def test_classify_critical_paths() -> None:
    assert classify("/etc/passwd", ChangeType.MODIFIED) is Severity.HIGH
    assert classify("/etc/ssh/sshd_config", ChangeType.MODIFIED) is Severity.HIGH
    assert classify("/var/tmp/x", ChangeType.ADDED) is Severity.LOW


def test_agent_tamper_is_critical() -> None:
    changes = diff_manifest({AGENT_SELF: "old"}, {AGENT_SELF: "new"})
    assert len(changes) == 1
    assert changes[0].severity is Severity.CRITICAL
    assert "변조" in changes[0].detail
