import pytest
from conftest import make_config, register_and_login
from flask import redirect

from app import create_app
from extensions import db, oauth
from models.user import User


@pytest.fixture
def google_app(tmp_path, monkeypatch):
    app = create_app(make_config(tmp_path, GOOGLE_CLIENT_ID="client-id", GOOGLE_CLIENT_SECRET="client-secret"))
    with app.app_context():
        db.create_all()

    profile = {
        "sub": "google-123",
        "email": "Grace@Example.com",
        "email_verified": True,
        "name": "Grace Hopper",
        "picture": "https://example.com/grace.png",
    }

    # Stand in for Google: the redirect goes nowhere and the code exchange returns our profile
    def fake_redirect(redirect_uri):
        return redirect(f"https://accounts.google.com/o/oauth2/auth?redirect_uri={redirect_uri}")

    monkeypatch.setattr(oauth.google, "authorize_redirect", fake_redirect)
    monkeypatch.setattr(oauth.google, "authorize_access_token", lambda: {"userinfo": profile})
    app.google_profile = profile
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def test_config_and_redirect(google_app):
    client = google_app.test_client()
    assert client.get("/auth/config").get_json() == {"google": True, "sandbox": False}
    response = client.get("/auth/google/login")
    assert response.status_code == 302
    assert "redirect_uri=http://localhost:5173/api/auth/google/callback" in response.location


def test_first_google_sign_in_creates_an_account(google_app):
    client = google_app.test_client()
    response = client.get("/auth/google/callback")
    assert response.status_code == 302
    assert response.location == "/auth/callback"
    assert client.get_cookie("refresh_token_cookie", path="/auth/") is not None

    with google_app.app_context():
        user = User.query.filter_by(google_sub="google-123").one()
        assert user.email == "grace@example.com"
        assert user.username == "grace"
        assert user.password is None
        assert user.avatar_url == "https://example.com/grace.png"

    # The refresh cookie is all the frontend needs to get an access token
    headers = {"X-CSRF-TOKEN": client.get_cookie("csrf_refresh_token").value}
    data = client.post("/auth/refresh", headers=headers).get_json()
    assert data["user"]["google_linked"] is True
    assert data["user"]["has_password"] is False


def test_returning_google_user_signs_into_the_same_account(google_app):
    client = google_app.test_client()
    client.get("/auth/google/callback")
    client.get("/auth/google/callback")
    with google_app.app_context():
        assert User.query.count() == 1


def test_google_only_account_cannot_use_password_login(google_app):
    client = google_app.test_client()
    client.get("/auth/google/callback")
    response = client.post("/auth/login", json={"username": "grace", "password": "anything123"})
    assert response.status_code == 400
    assert "Google" in response.get_json()["error"]


def test_existing_password_account_is_not_taken_over(google_app):
    client = google_app.test_client()
    client.post("/auth/register",
                json={"username": "squatter", "email": "grace@example.com", "password": "password123"})
    response = client.get("/auth/google/callback")
    assert response.location == "/login?error=account_exists"
    with google_app.app_context():
        assert User.query.filter_by(email="grace@example.com").one().google_sub is None


def test_unverified_google_email_is_rejected(google_app):
    google_app.google_profile["email_verified"] = False
    response = google_app.test_client().get("/auth/google/callback")
    assert response.location == "/login?error=google_unverified"


def test_signed_in_user_can_link_google(google_app):
    client = google_app.test_client()
    register_and_login(client, "grace_pw")  # login sets the refresh cookie
    assert client.get("/auth/google/login?intent=link").status_code == 302

    response = client.get("/auth/google/callback")
    assert response.location == "/chat?google=linked"
    with google_app.app_context():
        user = User.query.filter_by(username="grace_pw").one()
        assert user.google_sub == "google-123"
        assert user.password is not None


def test_linking_requires_a_session(google_app):
    response = google_app.test_client().get("/auth/google/login?intent=link")
    assert response.location == "/login?error=session_expired"
