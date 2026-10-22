import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient


def _register(client: TestClient, hostname: str) -> tuple[int, Ed25519PrivateKey]:
    asset_id: int = client.post("/assets", json={"hostname": hostname, "os": "ubuntu"}).json()["id"]
    priv = Ed25519PrivateKey.generate()
    pub = base64.b64encode(
        priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    client.put(f"/assets/{asset_id}/key", json={"public_key": pub})
    return asset_id, priv


def _signed_post(client: TestClient, path: str, priv: Ed25519PrivateKey, body: bytes) -> None:
    signature = base64.b64encode(priv.sign(body)).decode()
    resp = client.post(path, content=body, headers={"X-Signature": signature})
    assert resp.status_code == 201, resp.text


def test_summary_empty(client: TestClient) -> None:
    summary = client.get("/summary").json()
    assert summary["assets_total"] == 0
    assert summary["checks_fail"] == 0
    assert summary["remediations_open"] == 0


def test_summary_aggregates(client: TestClient) -> None:
    asset_id, priv = _register(client, "sum-01")
    client.post(f"/assets/{asset_id}/manage")
    _signed_post(
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
    summary = client.get("/summary").json()
    assert summary["assets_total"] == 1
    assert summary["assets_managed"] == 1
    assert summary["checks_fail"] >= 1  # U-01
    assert summary["checks_pass"] >= 1  # V-01 (trivy 없음 → pass)


def test_inventory_summary_endpoint(client: TestClient) -> None:
    asset_id, priv = _register(client, "sum-02")
    empty = client.get(f"/assets/{asset_id}/inventory").json()
    assert empty["package_count"] == 0
    assert empty["captured_at"] is None

    _signed_post(
        client,
        f"/assets/{asset_id}/inventory",
        priv,
        json.dumps(
            {"packages": [{"name": "openssl"}], "processes": [{"pid": 1, "name": "init"}]}
        ).encode(),
    )
    inv = client.get(f"/assets/{asset_id}/inventory").json()
    assert inv["package_count"] == 1
    assert inv["process_count"] == 1
    assert inv["captured_at"] is not None
