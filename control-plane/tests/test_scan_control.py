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


def _signed(client: TestClient, path: str, priv: Ed25519PrivateKey, body: bytes = b"") -> Response:
    sig = base64.b64encode(priv.sign(body)).decode()
    resp: Response = client.post(path, content=body, headers={"X-Signature": sig})
    return resp


def _enroll(client: TestClient, **create: str) -> tuple[int, Ed25519PrivateKey]:
    resp = client.post("/assets", json=create)
    assert resp.status_code == 201, resp.text
    asset_id = resp.json()["id"]
    priv, pub = _keypair()
    assert client.put(f"/assets/{asset_id}/key", json={"public_key": pub}).status_code == 200
    return asset_id, priv


def test_register_without_hostname_assigns_placeholder(client: TestClient) -> None:
    resp = client.post("/assets", json={"group": "운영"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["hostname"].startswith("pending-")
    assert body["health"] == "unknown"
    assert body["scan_paused"] is False
    assert body["address"] == ""


def test_inventory_autofills_hostname_and_address(client: TestClient) -> None:
    asset_id, priv = _enroll(client)  # hostname 미지정 → placeholder
    assert client.get(f"/assets/{asset_id}").json()["hostname"].startswith("pending-")

    body = json.dumps(
        {
            "host": {
                "hostname": "web-01",
                "address": "10.0.0.12",
                "os": "ubuntu",
                "os_version": "24.04",
            },
            "packages": [],
            "processes": [],
        }
    ).encode()
    assert _signed(client, f"/assets/{asset_id}/inventory", priv, body).status_code == 201

    asset = client.get(f"/assets/{asset_id}").json()
    assert asset["hostname"] == "web-01"
    assert asset["address"] == "10.0.0.12"
    assert asset["os"] == "ubuntu"


def test_heartbeat_sets_health_online(client: TestClient) -> None:
    asset_id, priv = _enroll(client, hostname="hb-01")
    assert client.get(f"/assets/{asset_id}").json()["health"] == "unknown"

    resp = _signed(client, f"/assets/{asset_id}/heartbeat", priv)
    assert resp.status_code == 200, resp.text
    assert resp.json()["asset_id"] == asset_id

    asset = client.get(f"/assets/{asset_id}").json()
    assert asset["health"] == "online"
    assert asset["last_seen_at"] is not None


def test_pause_resume_gates_command_dispatch(client: TestClient) -> None:
    asset_id, priv = _enroll(client, hostname="pz-01")
    # 검사 요청 큐잉
    assert client.post(f"/assets/{asset_id}/scan-requests").status_code == 201

    # 일시정지 → pull은 빈 목록(명령은 pending 유지)
    assert client.post(f"/assets/{asset_id}/scans/pause").json()["scan_paused"] is True
    pulled = _signed(client, f"/assets/{asset_id}/commands/pull", priv)
    assert pulled.status_code == 200
    assert pulled.json() == []

    # 재개 → pull에서 명령 디스패치
    assert client.post(f"/assets/{asset_id}/scans/resume").json()["scan_paused"] is False
    pulled = _signed(client, f"/assets/{asset_id}/commands/pull", priv)
    assert len(pulled.json()) == 1
    assert pulled.json()[0]["kind"] == "scan"


def test_cancel_pending_request(client: TestClient) -> None:
    asset_id, _ = _enroll(client, hostname="cx-01")
    cmd_id = client.post(f"/assets/{asset_id}/scan-requests").json()["id"]

    resp = client.post(f"/assets/{asset_id}/scan-requests/{cmd_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"

    # 취소된 명령은 pull 대상에서 제외(대기 아님).
    listed = client.get(f"/assets/{asset_id}/scan-requests").json()
    assert listed[0]["status"] == "canceled"


def test_cancel_missing_command_404(client: TestClient) -> None:
    asset_id, _ = _enroll(client, hostname="cx-02")
    assert client.post(f"/assets/{asset_id}/scan-requests/9999/cancel").status_code == 404
