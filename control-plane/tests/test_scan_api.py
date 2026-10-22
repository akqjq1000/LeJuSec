import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from httpx import Response


def _keypair() -> tuple[Ed25519PrivateKey, str]:
    priv = Ed25519PrivateKey.generate()
    raw_pub = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return priv, base64.b64encode(raw_pub).decode()


def _register_with_key(client: TestClient, hostname: str) -> tuple[int, Ed25519PrivateKey]:
    asset_id: int = client.post("/assets", json={"hostname": hostname, "os": "ubuntu"}).json()["id"]
    priv, pub = _keypair()
    assert client.put(f"/assets/{asset_id}/key", json={"public_key": pub}).status_code == 200
    return asset_id, priv


def _post_scan(client: TestClient, asset_id: int, priv: Ed25519PrivateKey, body: bytes) -> Response:
    signature = base64.b64encode(priv.sign(body)).decode()
    response: Response = client.post(
        f"/assets/{asset_id}/scan",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"},
    )
    return response


def test_scan_ingest_and_results(client: TestClient) -> None:
    asset_id, priv = _register_with_key(client, "scan-01")
    body = json.dumps(
        {
            "findings": [
                {"tool": "openscap", "check_id": "rule_sshd_disable_root_login", "passed": False},
                {"tool": "openscap", "check_id": "rule_set_password_hashing", "passed": True},
                {"tool": "trivy", "check_id": "CVE-2024-9", "severity": "critical"},
            ]
        }
    ).encode()

    resp = _post_scan(client, asset_id, priv, body)
    assert resp.status_code == 201, resp.text
    ack = resp.json()
    assert ack["total"] >= 5
    assert ack["failed"] >= 2  # U-01(root SSH) + V-01(critical CVE)

    results = client.get(f"/assets/{asset_id}/results").json()
    by_id = {r["check_id"]: r for r in results}
    assert by_id["U-01"]["status"] == "fail"
    assert by_id["U-02"]["status"] == "pass"
    assert by_id["V-01"]["status"] == "fail"
    assert "CVE-2024-9" in by_id["V-01"]["evidence"]


def test_scan_requires_signature(client: TestClient) -> None:
    asset_id, _ = _register_with_key(client, "scan-02")
    resp = client.post(
        f"/assets/{asset_id}/scan",
        content=b'{"findings":[]}',
        headers={"X-Signature": "AAAA"},
    )
    assert resp.status_code == 401


def test_results_empty_before_scan(client: TestClient) -> None:
    asset_id, _ = _register_with_key(client, "scan-03")
    assert client.get(f"/assets/{asset_id}/results").json() == []


def test_checks_endpoints(client: TestClient) -> None:
    all_checks = client.get("/checks").json()
    assert len(all_checks) >= 5

    hits = client.get("/checks/search", params={"q": "root SSH 원격 접속"}).json()
    assert hits
    assert hits[0]["item"]["id"] == "U-01"
    assert hits[0]["score"] > 0
