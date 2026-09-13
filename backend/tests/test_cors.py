from fastapi.testclient import TestClient

ORIGIN = "https://team-directory.web.app"


def test_cross_origin_authorized_request_preflight(client: TestClient) -> None:
    response = client.options(
        "/api/people",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "access-control-allow-credentials" not in response.headers


def test_auth_error_is_readable_from_frontend(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Origin": ORIGIN})
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["cache-control"] == "no-store"


def test_unlisted_origin_is_not_allowed(client: TestClient) -> None:
    response = client.options(
        "/api/people",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
