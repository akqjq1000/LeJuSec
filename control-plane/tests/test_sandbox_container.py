import shutil

import pytest

from lejusec.config import settings
from lejusec.remediation import Remediation
from lejusec.sandbox import container_command, verify


def test_container_command_is_isolated() -> None:
    cmd = container_command("ubuntu:24.04", "echo ok")
    assert cmd[:5] == ["docker", "run", "--rm", "--network=none", "--memory=256m"]
    assert "ubuntu:24.04" in cmd
    assert cmd[-3:] == ["bash", "-c", "echo ok"]


def test_container_backend_requires_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sandbox_backend", "container")
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    rem = Remediation(check_id="U-01", title="t", script="sed -i 's/a/b/' f", rollback="cp f.bak f")
    result = verify(rem)
    assert result.sandbox == "container"
    assert result.ok is False
    assert "docker" in result.notes


def test_container_backend_rejects_unsafe_before_running(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sandbox_backend", "container")
    # docker가 있더라도 정적 분석에서 먼저 막혀 실행되지 않아야 한다.
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/docker")
    rem = Remediation(check_id="x", title="t", script="rm -rf /", rollback="cp f.bak f")
    result = verify(rem)
    assert result.ok is False
    assert result.sandbox == "container"
    assert "정적 분석" in result.notes
