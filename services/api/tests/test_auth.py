from conftest import register_user


async def test_register_sets_session_and_me_returns_user(client, credentials):
    response = await register_user(client, credentials)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == credentials["email"]
    assert body["display_name"] == credentials["display_name"]
    assert body["storage"] == {
        "used_bytes": 0,
        "limit_bytes": 20 * 1024**3,
        "percent": 0.0,
    }
    assert "password" not in response.text
    assert client.cookies.get("uvh_session")

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]


async def test_duplicate_email_is_rejected(client, credentials):
    assert (await register_user(client, credentials)).status_code == 201
    duplicate = await register_user(client, credentials)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict_duplicate"


async def test_weak_password_is_rejected(client, credentials):
    weak = {**credentials, "password": "short"}
    response = await register_user(client, weak)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "weak_password"


async def test_login_logout_flow(client, credentials):
    await register_user(client, credentials)
    await client.post("/api/v1/auth/logout")
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": "password-salah-2026"},
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "invalid_credentials"

    good = await client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )
    assert good.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 200


async def test_logout_revokes_session_server_side(client, credentials):
    await register_user(client, credentials)
    token = client.cookies.get("uvh_session")
    assert token

    await client.post("/api/v1/auth/logout")
    # Replay the old cookie: the server-side session must stay revoked.
    client.cookies.set("uvh_session", token)
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_me_requires_session(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_foreign_origin_is_rejected(client, credentials):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
        headers={"origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_allowed_origin_passes(client, credentials):
    response = await client.post(
        "/api/v1/auth/register",
        json=credentials,
        headers={"origin": "http://localhost:3000"},
    )
    assert response.status_code == 201


async def test_login_rate_limit(client, credentials, monkeypatch):
    from app.services.auth import login_email_limiter, login_ip_limiter

    monkeypatch.setattr(login_ip_limiter, "limit", 2)
    monkeypatch.setattr(login_email_limiter, "limit", 2)
    payload = {"email": credentials["email"], "password": "salah-terus-2026"}
    assert (await client.post("/api/v1/auth/login", json=payload)).status_code == 401
    assert (await client.post("/api/v1/auth/login", json=payload)).status_code == 401
    limited = await client.post("/api/v1/auth/login", json=payload)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert limited.headers["retry-after"]


async def test_validation_error_envelope(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "x", "display_name": ""},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]["errors"]
