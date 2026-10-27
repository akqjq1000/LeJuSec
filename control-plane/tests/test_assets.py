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


def test_group_on_register_and_update(client: TestClient) -> None:
    # 등록 시 그룹 지정
    resp = client.post("/assets", json={"hostname": "g-01", "group": "운영-웹"})
    assert resp.status_code == 201, resp.text
    asset_id = resp.json()["id"]
    assert resp.json()["group"] == "운영-웹"

    # 기존 자산 그룹 변경
    resp = client.put(f"/assets/{asset_id}/group", json={"group": "DB"})
    assert resp.status_code == 200
    assert resp.json()["group"] == "DB"

    # 그룹 목록(중복 제거)
    client.post("/assets", json={"hostname": "g-02", "group": "DB"})
    groups = client.get("/assets/groups").json()
    assert groups == ["DB"]

    # 그룹 해제(빈 값)
    assert client.put(f"/assets/{asset_id}/group", json={"group": ""}).json()["group"] == ""


def test_group_registry(client: TestClient) -> None:
    # 빈 그룹 생성(자산 없이도 목록에 유지)
    assert client.post("/asset-groups", json={"name": "운영-웹"}).status_code == 201
    assert "운영-웹" in client.get("/asset-groups").json()

    # 중복 생성 409
    assert client.post("/asset-groups", json={"name": "운영-웹"}).status_code == 409

    # 레지스트리 ∪ 자산 지정 그룹
    client.post("/assets", json={"hostname": "gr-01", "group": "DB"})
    assert set(client.get("/asset-groups").json()) >= {"운영-웹", "DB"}

    # 그룹 삭제 → 소속 자산은 미분류로
    aid = client.get("/assets").json()[0]["id"]
    client.put(f"/assets/{aid}/group", json={"group": "운영-웹"})
    assert client.delete("/asset-groups/운영-웹").status_code == 204
    assert "운영-웹" not in client.get("/asset-groups").json()
    assert client.get(f"/assets/{aid}").json()["group"] == ""
