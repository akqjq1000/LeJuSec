import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from httpx import Response


def _register_with_key(client: TestClient, hostname: str) -> tuple[int, Ed25519PrivateKey]:
    asset_id: int = client.post("/assets", json={"hostname": hostname, "os": "ubuntu"}).json()["id"]
    priv = Ed25519PrivateKey.generate()
    pub = base64.b64encode(
        priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    client.put(f"/assets/{asset_id}/key", json={"public_key": pub})
    return asset_id, priv


def _signed(client: TestClient, path: str, priv: Ed25519PrivateKey, body: bytes) -> Response:
    signature = base64.b64encode(priv.sign(body)).decode()
    response: Response = client.post(path, content=body, headers={"X-Signature": signature})
    return response


def test_audit_records_asset_actions(client: TestClient) -> None:
    asset_id: int = client.post("/assets", json={"hostname": "aud-01", "os": "ubuntu"}).json()["id"]
    client.post(f"/assets/{asset_id}/manage")

    audit = client.get("/audit").json()
    actions = [a["action"] for a in audit]
    assert "asset.register" in actions
    assert "asset.manage" in actions
    assert all(a["actor"] == "dev" for a in audit)  # 인증 비활성 → dev


def test_audit_records_remediation_decision(client: TestClient) -> None:
    asset_id, priv = _register_with_key(client, "aud-02")
    _signed(
        client,
        f"/assets/{asset_id}/scan",
        priv,
        json.dumps(
            {
                "findings": [
                    {
                        "tool": "openscap",
                        "check_id": "rule_sshd_disable_root_login",
                        "passed": False,
                    }
                ]
            }
        ).encode(),
    )
    gen = client.post(f"/assets/{asset_id}/remediations").json()
    rid = gen["proposed"][0]["id"]
    client.post(f"/remediations/{rid}/approve")

    actions = [a["action"] for a in client.get("/audit").json()]
    assert "remediation.approve" in actions


def test_integrity_sse_once(client: TestClient) -> None:
    asset_id, priv = _register_with_key(client, "aud-03")
    base = f"/assets/{asset_id}/integrity"
    _signed(
        client,
        f"{base}?baseline=true",
        priv,
        json.dumps({"files": [{"path": "/etc/x", "sha256": "1"}]}).encode(),
    )
    _signed(client, base, priv, json.dumps({"files": [{"path": "/etc/x", "sha256": "2"}]}).encode())

    resp = client.get("/events/integrity?once=true")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "data:" in resp.text
    assert "/etc/x" in resp.text


def test_integrity_sse_once_empty(client: TestClient) -> None:
    resp = client.get("/events/integrity?once=true")
    assert resp.status_code == 200
    assert "event: end" in resp.text
