import base64
import json
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from lejusec.config import settings

ADMIN = {"Authorization": "Bearer admintok"}
VIEWER = {"Authorization": "Bearer viewtok"}


@pytest.fixture
def auth_enabled(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "operator_tokens", "admintok:admin,viewtok:viewer")
    yield


def _register_signed_asset(client: TestClient, hostname: str) -> tuple[int, Ed25519PrivateKey]:
    asset_id: int = client.post("/assets", json={"hostname": hostname, "os": "ubuntu"}).json()["id"]
    priv = Ed25519PrivateKey.generate()
    pub = base64.b64encode(
        priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    client.put(f"/assets/{asset_id}/key", json={"public_key": pub})
    return asset_id, priv


def _signed(priv: Ed25519PrivateKey, body: bytes) -> dict[str, str]:
    return {"X-Signature": base64.b64encode(priv.sign(body)).decode()}


def test_scan_request_pull_report_roundtrip(client: TestClient) -> None:
    asset_id, priv = _register_signed_asset(client, "cmd-01")

    # 운영자: 검사 요청 큐잉
    created = client.post(f"/assets/{asset_id}/scan-requests")
    assert created.status_code == 201, created.text
    cmd = created.json()
    assert cmd["kind"] == "scan"
    assert cmd["status"] == "pending"

    # 에이전트: 서명된 빈 바디로 pull → claimed
    pulled = client.post(
        f"/assets/{asset_id}/commands/pull", content=b"", headers=_signed(priv, b"")
    )
    assert pulled.status_code == 200, pulled.text
    commands = pulled.json()
    assert len(commands) == 1
    assert commands[0]["id"] == cmd["id"]
    assert commands[0]["kind"] == "scan"

    # 재pull 시 이미 claimed → 빈 목록
    again = client.post(
        f"/assets/{asset_id}/commands/pull", content=b"", headers=_signed(priv, b"")
    )
    assert again.json() == []

    # 에이전트: 결과 보고
    report = json.dumps({"results": [{"id": cmd["id"], "status": "done", "result": "2 findings"}]})
    body = report.encode()
    reported = client.post(
        f"/assets/{asset_id}/commands/report", content=body, headers=_signed(priv, body)
    )
    assert reported.status_code == 200, reported.text
    assert reported.json()["updated"] == 1

    # 운영자: 상태 조회 → done
    listed = client.get(f"/assets/{asset_id}/scan-requests").json()
    assert listed[0]["status"] == "done"
    assert listed[0]["result"] == "2 findings"
    assert listed[0]["done_at"] is not None


def test_pull_requires_signature(client: TestClient) -> None:
    asset_id, _ = _register_signed_asset(client, "cmd-02")
    client.post(f"/assets/{asset_id}/scan-requests")
    # 서명 헤더 없음 → 거부(400/401 계열)
    resp = client.post(f"/assets/{asset_id}/commands/pull", content=b"")
    assert resp.status_code >= 400


def test_scan_request_rbac(client: TestClient, auth_enabled: None) -> None:
    asset_id: int = client.post(
        "/assets", json={"hostname": "cmd-03", "os": "ubuntu"}, headers=ADMIN
    ).json()["id"]
    # viewer는 쓰기 불가
    assert client.post(f"/assets/{asset_id}/scan-requests", headers=VIEWER).status_code == 403
    # admin은 가능
    assert client.post(f"/assets/{asset_id}/scan-requests", headers=ADMIN).status_code == 201
    # viewer도 조회는 가능
    assert client.get(f"/assets/{asset_id}/scan-requests", headers=VIEWER).status_code == 200
