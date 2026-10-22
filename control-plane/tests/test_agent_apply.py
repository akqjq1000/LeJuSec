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


def _scan_fail(client: TestClient, asset_id: int, priv: Ed25519PrivateKey) -> None:
    body = json.dumps(
        {
            "findings": [
                {"tool": "openscap", "check_id": "rule_sshd_disable_root_login", "passed": False}
            ]
        }
    ).encode()
    assert _signed(client, f"/assets/{asset_id}/scan", priv, body).status_code == 201


def _setup_approved(client: TestClient, hostname: str) -> tuple[int, Ed25519PrivateKey, int]:
    asset_id, priv = _register_with_key(client, hostname)
    _scan_fail(client, asset_id, priv)
    gen = client.post(f"/assets/{asset_id}/remediations").json()
    rid: int = gen["proposed"][0]["id"]
    assert client.post(f"/remediations/{rid}/approve").status_code == 200
    return asset_id, priv, rid


def test_pull_apply_report_flow(client: TestClient) -> None:
    asset_id, priv, rid = _setup_approved(client, "ap-01")

    pulled = _signed(client, f"/assets/{asset_id}/remediations/pull", priv, b"")
    assert pulled.status_code == 200
    approved = pulled.json()
    assert any(a["id"] == rid for a in approved)
    assert all("script" in a and "rollback" in a for a in approved)

    report = _signed(
        client,
        f"/assets/{asset_id}/remediations/report",
        priv,
        json.dumps({"results": [{"id": rid, "status": "applied", "output": "exit 0"}]}).encode(),
    )
    assert report.status_code == 200
    assert report.json()["updated"] == 1

    # 적용 후에는 pull 대상에서 빠진다
    again = _signed(client, f"/assets/{asset_id}/remediations/pull", priv, b"").json()
    assert all(a["id"] != rid for a in again)

    rems = client.get(f"/assets/{asset_id}/remediations").json()
    row = next(x for x in rems if x["id"] == rid)
    assert row["apply_status"] == "applied"

    actions = [a["action"] for a in client.get("/audit").json()]
    assert "remediation.apply" in actions


def test_pull_requires_signature(client: TestClient) -> None:
    asset_id, _, _ = _setup_approved(client, "ap-02")
    resp = client.post(
        f"/assets/{asset_id}/remediations/pull", content=b"", headers={"X-Signature": "AAAA"}
    )
    assert resp.status_code == 401


def test_pull_excludes_unapproved(client: TestClient) -> None:
    asset_id, priv = _register_with_key(client, "ap-03")
    _scan_fail(client, asset_id, priv)
    client.post(f"/assets/{asset_id}/remediations")  # proposed, 미승인
    assert _signed(client, f"/assets/{asset_id}/remediations/pull", priv, b"").json() == []
