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


def test_open_when_no_tokens(client: TestClient) -> None:
    # 기본값: 토큰 미설정 → 인증 비활성
    assert client.get("/summary").status_code == 200
    assert client.get("/me").json()["role"] == "admin"


def test_requires_token(client: TestClient, auth_enabled: None) -> None:
    assert client.get("/summary").status_code == 401
    assert client.get("/me").status_code == 401


def test_viewer_reads_but_cannot_write(client: TestClient, auth_enabled: None) -> None:
    assert client.get("/summary", headers=VIEWER).status_code == 200
    assert client.get("/me", headers=VIEWER).json()["role"] == "viewer"
    resp = client.post("/assets", json={"hostname": "a", "os": "ubuntu"}, headers=VIEWER)
    assert resp.status_code == 403


def test_admin_can_write(client: TestClient, auth_enabled: None) -> None:
    resp = client.post("/assets", json={"hostname": "b", "os": "ubuntu"}, headers=ADMIN)
    assert resp.status_code == 201


def test_agent_signed_bypasses_operator_auth(client: TestClient, auth_enabled: None) -> None:
    # 자산 등록·공개키 등록은 admin으로, 서명 인벤토리 전송은 운영자 토큰 없이.
    asset_id: int = client.post(
        "/assets", json={"hostname": "c", "os": "ubuntu"}, headers=ADMIN
    ).json()["id"]
    priv = Ed25519PrivateKey.generate()
    pub = base64.b64encode(
        priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    client.put(f"/assets/{asset_id}/key", json={"public_key": pub}, headers=ADMIN)

    body = json.dumps({"packages": [], "processes": []}).encode()
    signature = base64.b64encode(priv.sign(body)).decode()
    # 운영자 토큰 없이 서명만으로 통과해야 한다.
    resp = client.post(
        f"/assets/{asset_id}/inventory",
        content=body,
        headers={"X-Signature": signature},
    )
    assert resp.status_code == 201, resp.text
