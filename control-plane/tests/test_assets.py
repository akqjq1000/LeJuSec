from fastapi.testclient import TestClient


def _register(client: TestClient, hostname: str = "web-01") -> dict[str, object]:
    resp = client.post(
        "/assets", json={"hostname": hostname, "os": "ubuntu", "os_version": "24.04"}
    )
    assert resp.status_code == 201, resp.text
    body: dict[str, object] = resp.json()
    return body


def test_register_and_get(client: TestClient) -> None:
    created = _register(client)
    assert created["hostname"] == "web-01"
    assert created["managed"] is False
    asset_id = created["id"]

    resp = client.get(f"/assets/{asset_id}")
    assert resp.status_code == 200
    assert resp.json()["os"] == "ubuntu"


def test_duplicate_hostname_conflict(client: TestClient) -> None:
    _register(client)
    resp = client.post("/assets", json={"hostname": "web-01", "os": "ubuntu"})
    assert resp.status_code == 409


def test_manage_and_unmanage(client: TestClient) -> None:
    asset_id = _register(client)["id"]

    resp = client.post(f"/assets/{asset_id}/manage")
    assert resp.status_code == 200
    assert resp.json()["managed"] is True

    resp = client.post(f"/assets/{asset_id}/unmanage")
    assert resp.status_code == 200
    assert resp.json()["managed"] is False


def test_list_and_deregister(client: TestClient) -> None:
    _register(client, "web-01")
    _register(client, "web-02")
    assert len(client.get("/assets").json()) == 2

    asset_id = client.get("/assets").json()[0]["id"]
    assert client.delete(f"/assets/{asset_id}").status_code == 204
    assert len(client.get("/assets").json()) == 1


def test_get_missing_404(client: TestClient) -> None:
    assert client.get("/assets/9999").status_code == 404
