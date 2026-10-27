import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient


def _keypair() -> tuple[Ed25519PrivateKey, str]:
    priv = Ed25519PrivateKey.generate()
    raw_pub = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return priv, base64.b64encode(raw_pub).decode()


def _register(client: TestClient, hostname: str) -> int:
    resp = client.post("/assets", json={"hostname": hostname, "os": "ubuntu"})
    assert resp.status_code == 201, resp.text
    asset_id: int = resp.json()["id"]
    return asset_id


def test_signed_inventory_ingest(client: TestClient) -> None:
    asset_id = _register(client, "sig-01")
    priv, pub_b64 = _keypair()
    assert client.put(f"/assets/{asset_id}/key", json={"public_key": pub_b64}).status_code == 200

    body = json.dumps(
        {
            "packages": [{"name": "openssl", "version": "3.0.2", "source": "dpkg"}],
            "processes": [{"pid": 1, "name": "systemd", "exe": "/sbin/init"}],
        }
    ).encode()
    signature = base64.b64encode(priv.sign(body)).decode()

    resp = client.post(
        f"/assets/{asset_id}/inventory",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 201, resp.text
    ack = resp.json()
    assert ack["package_count"] == 1
    assert ack["process_count"] == 1

    asset = client.get(f"/assets/{asset_id}").json()
    assert asset["last_scan_at"] is not None
    assert asset["agent_status"] == "reporting"


def test_os_auto_detected_from_inventory(client: TestClient) -> None:
    # OS 없이 등록하면 pending 상태가 된다.
    resp = client.post("/assets", json={"hostname": "auto-01"})
    assert resp.status_code == 201, resp.text
    asset_id = resp.json()["id"]
    assert resp.json()["os"] == "pending"

    priv, pub_b64 = _keypair()
    client.put(f"/assets/{asset_id}/key", json={"public_key": pub_b64})

    # 에이전트 인벤토리에 동봉된 host 정보로 OS가 자동 탐지되어야 한다.
    body = json.dumps(
        {
            "host": {"os": "ubuntu", "os_version": "24.04", "family": "linux", "arch": "amd64"},
            "packages": [],
            "processes": [],
        }
    ).encode()
    signature = base64.b64encode(priv.sign(body)).decode()
    resp = client.post(
        f"/assets/{asset_id}/inventory",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"},
    )
    assert resp.status_code == 201, resp.text

    asset = client.get(f"/assets/{asset_id}").json()
    assert asset["os"] == "ubuntu"
    assert asset["os_version"] == "24.04"


def test_tampered_body_rejected(client: TestClient) -> None:
    asset_id = _register(client, "sig-02")
    priv, pub_b64 = _keypair()
    client.put(f"/assets/{asset_id}/key", json={"public_key": pub_b64})

    body = b'{"packages":[],"processes":[]}'
    signature = base64.b64encode(priv.sign(body)).decode()
    tampered = b'{"packages":[{"name":"evil"}],"processes":[]}'

    resp = client.post(
        f"/assets/{asset_id}/inventory",
        content=tampered,
        headers={"X-Signature": signature},
    )
    assert resp.status_code == 401


def test_missing_signature_rejected(client: TestClient) -> None:
    asset_id = _register(client, "sig-03")
    _, pub_b64 = _keypair()
    client.put(f"/assets/{asset_id}/key", json={"public_key": pub_b64})

    resp = client.post(f"/assets/{asset_id}/inventory", content=b"{}")
    assert resp.status_code == 401


def test_no_key_registered_rejected(client: TestClient) -> None:
    asset_id = _register(client, "sig-04")
    resp = client.post(
        f"/assets/{asset_id}/inventory",
        content=b'{"packages":[],"processes":[]}',
        headers={"X-Signature": "AAAA"},
    )
    assert resp.status_code == 409
