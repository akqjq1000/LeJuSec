from fastapi.testclient import TestClient


def test_install_script_served_with_server_filled(client: TestClient) -> None:
    resp = client.get("/install.sh")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    # 스크립트 본문이 맞는지 + 자리표시자가 베이스 URL로 치환됐는지 확인.
    assert "LeJuSec 에이전트 원샷 설치" in body
    assert "@@DEFAULT_SERVER@@" not in body
    assert 'DEFAULT_SERVER="http://testserver"' in body


def test_install_script_open_without_token() -> None:
    # 운영자 토큰이 설정돼도 /install.sh 는 토큰 없이 받을 수 있어야 한다.
    from lejusec.config import settings

    original = settings.operator_tokens
    settings.operator_tokens = "secret:admin"
    try:
        from lejusec.main import app

        with TestClient(app) as c:
            assert c.get("/install.sh").status_code == 200
            # 보호된 쓰기 엔드포인트는 토큰 없이는 거부.
            assert c.post("/assets", json={"hostname": "x"}).status_code == 401
    finally:
        settings.operator_tokens = original
