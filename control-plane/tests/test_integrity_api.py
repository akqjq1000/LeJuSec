import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from httpx import Response


def _register(client: TestClient, hostname: str) -> tuple[int, Ed25519PrivateKey]:
    asset_id: int = client.post("/assets", json={"hostname": hostname, "os": "ubuntu"}).json()["id"]
    priv = Ed25519PrivateKey.generate()
    pub = base64.b64encode(
        priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    client.put(f"/assets/{asset_id}/key", json={"public_key": pub})
    return asset_id, priv


def _post(
    client: TestClient,
    asset_id: int,
    priv: Ed25519PrivateKey,
    manifest: dict[str, object],
    *,
    baseline: bool = False,
) -> Response:
    body = json.dumps(manifest).encode()
    signature = base64.b64encode(priv.sign(body)).decode()
    url = f"/assets/{asset_id}/integrity" + ("?baseline=true" if baseline else "")
    response: Response = client.post(url, content=body, headers={"X-Signature": signature})
    return response


def test_baseline_then_detect(client: TestClient) -> None:
    asset_id, priv = _register(client, "fim-01")

    baseline_manifest: dict[str, object] = {
        "agent_sha256": "AAA",
        "files": [
            {"path": "/etc/ssh/sshd_config", "sha256": "h1"},
            {"path": "/etc/motd", "sha256": "m1"},
        ],
    }
    first = _post(client, asset_id, priv, baseline_manifest)
    assert first.status_code == 201, first.text
    assert first.json()["baseline_established"] is True
    assert first.json()["baseline_files"] == 3  # 2 files + agent:self

    changed: dict[str, object] = {
        "agent_sha256": "BBB",
        "files": [
            {"path": "/etc/ssh/sshd_config", "sha256": "h2"},
            {"path": "/etc/motd", "sha256": "m1"},
        ],
    }
    second = _post(client, asset_id, priv, changed).json()
    assert second["baseline_established"] is False
    assert second["changes"] == 2  # sshd_config 수정 + agent 변조
    assert second["critical"] == 1  # agent:self
    assert second["high"] == 1  # /etc/ssh/sshd_config

    events = client.get(f"/assets/{asset_id}/integrity/events").json()
    paths = {e["path"] for e in events}
    assert "agent:self" in paths
    assert "/etc/ssh/sshd_config" in paths

    summary = client.get(f"/assets/{asset_id}/integrity/baseline").json()
    assert summary["files"] == 2
    assert summary["has_agent_hash"] is True


def test_integrity_requires_signature(client: TestClient) -> None:
    asset_id, _ = _register(client, "fim-02")
    resp = client.post(
        f"/assets/{asset_id}/integrity",
        content=b'{"files":[]}',
        headers={"X-Signature": "AAAA"},
    )
    assert resp.status_code == 401


def test_rebaseline(client: TestClient) -> None:
    asset_id, priv = _register(client, "fim-03")
    _post(client, asset_id, priv, {"files": [{"path": "/a", "sha256": "1"}]})
    rebaselined = _post(
        client,
        asset_id,
        priv,
        {"files": [{"path": "/a", "sha256": "2"}, {"path": "/b", "sha256": "3"}]},
        baseline=True,
    ).json()
    assert rebaselined["baseline_established"] is True
    assert rebaselined["baseline_files"] == 2
