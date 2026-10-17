from conftest import register_and_login


def login(client, username="alice", password="password123"):
    return client.post("/auth/login", json={"username": username, "password": password})


def csrf(client):
    return {"X-CSRF-TOKEN": client.get_cookie("csrf_refresh_token").value}


def refresh_cookie(client):
    cookie = client.get_cookie("refresh_token_cookie", path="/auth/")
    return cookie.value if cookie else None


def test_login_sets_httponly_refresh_cookie(client):
    register_and_login(client)
    response = login(client)
    cookies = response.headers.getlist("Set-Cookie")
    refresh = next(c for c in cookies if c.startswith("refresh_token_cookie="))
    assert "HttpOnly" in refresh
    assert "SameSite=Strict" in refresh
    assert "Path=/auth/" in refresh
    assert any(c.startswith("csrf_refresh_token=") and "HttpOnly" not in c for c in cookies)


def test_login_accepts_email(client):
    register_and_login(client)
    response = client.post("/auth/login", json={"username": "ALICE@example.com", "password": "password123"})
    assert response.status_code == 200


def test_refresh_rotates_the_token(client):
    register_and_login(client)
    login(client)
    first = refresh_cookie(client)

    response = client.post("/auth/refresh", headers=csrf(client))
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["username"] == "alice"
    assert refresh_cookie(client) != first

    profile = client.get("/auth/profile", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert profile.status_code == 200


def test_refresh_requires_csrf_header(client):
    register_and_login(client)
    login(client)
    assert client.post("/auth/refresh").status_code == 401


def _client_with(app, refresh_token, csrf_token):
    other = app.test_client()
    other.set_cookie("refresh_token_cookie", refresh_token, path="/auth/")
    other.set_cookie("csrf_refresh_token", csrf_token)
    return other


def test_replayed_refresh_token_revokes_every_session(client, app):
    register_and_login(client)
    login(client)
    stolen = refresh_cookie(client)
    headers = csrf(client)

    assert client.post("/auth/refresh", headers=headers).status_code == 200  # legitimate rotation
    current = refresh_cookie(client)

    # An attacker replays the old token: it is rejected, and the legitimate session is ended too
    attacker = _client_with(app, stolen, headers["X-CSRF-TOKEN"])
    assert attacker.post("/auth/refresh", headers=headers).status_code == 401

    victim = _client_with(app, current, client.get_cookie("csrf_refresh_token").value)
    assert victim.post("/auth/refresh", headers=csrf(victim)).status_code == 401


def test_logout_revokes_refresh_token(client, app):
    register_and_login(client)
    login(client)
    token = refresh_cookie(client)
    headers = csrf(client)

    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert refresh_cookie(client) is None

    replay = _client_with(app, token, headers["X-CSRF-TOKEN"])
    assert replay.post("/auth/refresh", headers=headers).status_code == 401


def test_logout_without_session_still_succeeds(client):
    assert client.post("/auth/logout").status_code == 200


def test_auth_config_reports_google_disabled(client):
    assert client.get("/auth/config").get_json() == {"google": False, "sandbox": False}
    assert client.get("/auth/google/login").status_code == 404
