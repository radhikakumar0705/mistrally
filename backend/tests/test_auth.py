from conftest import make_config

from app import create_app
from extensions import db, limiter


def test_register_validates_input(client):
    cases = [
        ({"username": "a", "email": "a@x.io"}, "Missing required fields"),
        ({"username": "a", "email": "not-an-email", "password": "password123"}, "Invalid email address"),
        ({"username": "a", "email": "a@x.io", "password": "short"}, "at least 8 characters"),
        ({"username": "a" * 51, "email": "a@x.io", "password": "password123"}, "50 characters"),
    ]
    for body, expected in cases:
        response = client.post("/auth/register", json=body)
        assert response.status_code == 400
        assert expected in response.get_json()["error"]


def test_register_and_login(client):
    body = {"username": "alice", "email": "Alice@Example.com", "password": "password123"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409

    response = client.post("/auth/login", json={"username": "alice", "password": "password123"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["access_token"]
    assert data["user"]["email"] == "alice@example.com"


def test_login_rejects_wrong_password(client):
    client.post("/auth/register", json={"username": "bob", "email": "b@x.io", "password": "password123"})
    response = client.post("/auth/login", json={"username": "bob", "password": "wrong-password"})
    assert response.status_code == 401


def test_profile_requires_valid_token(client, auth):
    assert client.get("/auth/profile", headers=auth).get_json()["username"] == "alice"
    assert client.get("/auth/profile").status_code == 401
    assert client.get("/auth/profile", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_login_is_rate_limited(tmp_path):
    app = create_app(make_config(tmp_path, RATELIMIT_ENABLED=True))
    with app.app_context():
        db.create_all()
        limiter.reset()
    client = app.test_client()

    statuses = [client.post("/auth/login", json={"username": "x", "password": "y"}).status_code
                for _ in range(11)]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
    assert "Too many requests" in client.post("/auth/login", json={}).get_json()["error"]


def test_health_endpoints(client):
    assert client.get("/health/live").status_code == 200
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.get_json()["database"] == "up"
