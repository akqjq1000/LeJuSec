import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient


def _setup_failing_scan(client: TestClient, hostname: str) -> int:
    asset_id: int = client.post("/assets", json={"hostname": hostname, "os": "ubuntu"}).json()["id"]
    priv = Ed25519PrivateKey.generate()
    pub = base64.b64encode(
        priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    ).decode()
    client.put(f"/assets/{asset_id}/key", json={"public_key": pub})

    body = json.dumps(
        {
            "findings": [
                {"tool": "openscap", "check_id": "rule_sshd_disable_root_login", "passed": False},
                {"tool": "lynis", "check_id": "AUTH-9286", "passed": False},
            ]
        }
    ).encode()
    signature = base64.b64encode(priv.sign(body)).decode()
    resp = client.post(f"/assets/{asset_id}/scan", content=body, headers={"X-Signature": signature})
    assert resp.status_code == 201, resp.text
    return asset_id


def test_generate_verify_approve(client: TestClient) -> None:
    asset_id = _setup_failing_scan(client, "rem-01")

    gen = client.post(f"/assets/{asset_id}/remediations").json()
    assert gen["generated"] >= 2  # U-01(root SSH) + U-04(password aging)
    proposed = gen["proposed"]
    assert all(p["status"] == "proposed" for p in proposed)
    assert all(p["static_ok"] for p in proposed)  # 템플릿은 정적 분석 통과

    rid = proposed[0]["id"]
    verify_out = client.post(f"/remediations/{rid}/verify").json()
    assert verify_out["ok"] is True
    assert verify_out["sandbox"] == "dry-run"

    approved = client.post(f"/remediations/{rid}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    # 이미 승인됨 → 재승인 불가
    assert client.post(f"/remediations/{rid}/approve").status_code == 409


def test_list_and_reject(client: TestClient) -> None:
    asset_id = _setup_failing_scan(client, "rem-02")
    client.post(f"/assets/{asset_id}/remediations")

    rems = client.get(f"/assets/{asset_id}/remediations").json()
    assert rems
    rid = rems[0]["id"]
    assert client.post(f"/remediations/{rid}/reject").json()["status"] == "rejected"


def test_generate_without_scan(client: TestClient) -> None:
    asset_id: int = client.post("/assets", json={"hostname": "rem-empty", "os": "ubuntu"}).json()[
        "id"
    ]
    gen = client.post(f"/assets/{asset_id}/remediations").json()
    assert gen["generated"] == 0
