"""HTTP layer for accounts and sessions: cookies, redirects and tokens around AuthService."""
from authlib.integrations.base_client.errors import OAuthError
from flask import Blueprint, current_app, jsonify, redirect, request, session
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_refresh_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
)

from extensions import limiter, oauth
from services import token_service
from services.auth_service import AuthService, GoogleSignInError
from services.errors import Unauthorized

auth_bp = Blueprint("auth", __name__)

LINK_INTENT_KEY = "oauth_link_user_id"


def _google_enabled():
    config = current_app.config
    return bool(config.get("GOOGLE_CLIENT_ID") and config.get("GOOGLE_CLIENT_SECRET"))


def _session_response(user):
    """JSON with a fresh access token, plus the refresh token in an httpOnly cookie."""
    access, refresh = token_service.issue_tokens(user.id)
    response = jsonify({"access_token": access, "user": user.to_dict()})
    set_refresh_cookies(response, refresh)
    return response, 200


@auth_bp.route("/config", methods=["GET"])
def auth_config():
    """Which sign-in methods and optional features the frontend should offer."""
    return jsonify({"google": _google_enabled(), "sandbox": bool(current_app.config.get("SANDBOX_URL"))}), 200


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5/minute")
def register():
    body = request.get_json(silent=True) or {}
    AuthService().register(body.get("username"), body.get("email"), body.get("password"))
    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10/minute")
def login():
    body = request.get_json(silent=True) or {}
    user = AuthService().authenticate(body.get("username"), body.get("password"))
    return _session_response(user)


@auth_bp.route("/refresh", methods=["POST"])
@limiter.limit("30/minute")
@jwt_required(refresh=True)
def refresh():
    """Trade the refresh cookie (plus its CSRF header) for a new access token; the cookie is rotated."""
    try:
        user = AuthService().profile(int(get_jwt_identity()))
    except Exception as e:
        raise Unauthorized("User not found") from e
    access, new_refresh = token_service.rotate(get_jwt()["jti"], user.id)
    response = jsonify({"access_token": access, "user": user.to_dict()})
    set_refresh_cookies(response, new_refresh)
    return response, 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    try:
        verify_jwt_in_request(refresh=True, optional=True)
        claims = get_jwt()
        if claims:
            token_service.revoke(claims["jti"])
    except Exception:
        pass  # an expired or invalid cookie still gets cleared below
    response = jsonify({"message": "Logged out"})
    unset_jwt_cookies(response)
    return response, 200


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    return jsonify(AuthService().profile(int(get_jwt_identity())).to_dict()), 200


# ---- Google sign-in (OAuth 2.0 authorization code flow with PKCE, via Authlib) ----

def _google_redirect_uri():
    return f"{current_app.config['PUBLIC_URL']}/api/auth/google/callback"


@auth_bp.route("/google/login", methods=["GET"])
@limiter.limit("20/minute")
def google_login():
    if not _google_enabled():
        return jsonify({"error": "Google sign-in is not configured"}), 404

    session.pop(LINK_INTENT_KEY, None)
    if request.args.get("intent") == "link":
        # Connecting Google to the signed-in account: identify the user from their refresh cookie
        try:
            verify_jwt_in_request(refresh=True, locations=["cookies"])
        except Exception:
            return redirect("/login?error=session_expired")
        session[LINK_INTENT_KEY] = int(get_jwt_identity())

    return oauth.google.authorize_redirect(_google_redirect_uri())


@auth_bp.route("/google/callback", methods=["GET"])
def google_callback():
    if not _google_enabled():
        return redirect("/login?error=google_disabled")

    try:
        token = oauth.google.authorize_access_token()  # validates state, PKCE and the ID token's nonce
    except OAuthError as e:
        current_app.logger.warning("Google OAuth failed: %s", e)
        return redirect("/login?error=google_failed")

    info = token.get("userinfo") or {}
    link_user_id = session.pop(LINK_INTENT_KEY, None)
    service = AuthService()

    if link_user_id is not None:
        try:
            service.link_google(link_user_id, info)
        except GoogleSignInError as e:
            if e.code == "already_linked":
                return redirect("/chat?google=already_linked")
            return redirect(f"/login?error={e.code}")
        return redirect("/chat?google=linked")

    try:
        user = service.google_sign_in(info)
    except GoogleSignInError as e:
        return redirect(f"/login?error={e.code}")

    _access, refresh_token = token_service.issue_tokens(user.id)
    response = redirect("/auth/callback")
    set_refresh_cookies(response, refresh_token)
    return response
