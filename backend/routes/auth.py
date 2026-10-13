import re
import secrets

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

from extensions import db, limiter, oauth
from models.user import User
from services import token_service

auth_bp = Blueprint('auth', __name__)

MIN_PASSWORD_LENGTH = 8
LINK_INTENT_KEY = "oauth_link_user_id"


def _google_enabled():
    config = current_app.config
    return bool(config.get("GOOGLE_CLIENT_ID") and config.get("GOOGLE_CLIENT_SECRET"))


def _session_response(user, status=200):
    """JSON with a fresh access token, plus the refresh token in an httpOnly cookie."""
    access, refresh = token_service.issue_tokens(user.id)
    response = jsonify({"access_token": access, "user": user.to_dict()})
    set_refresh_cookies(response, refresh)
    return response, status


@auth_bp.route('/config', methods=['GET'])
def auth_config():
    """Which sign-in methods the frontend should offer."""
    return jsonify({"google": _google_enabled()}), 200


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5/minute")
def register():
    data = request.get_json(silent=True) or {}

    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
    if len(username) > 50:
        return jsonify({"error": "Username must be 50 characters or fewer"}), 400
    if '@' not in email:
        return jsonify({"error": "Invalid email address"}), 400
    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "User already exists"}), 409

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10/minute")
def login():
    data = request.get_json(silent=True) or {}

    identifier = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not identifier or not password:
        return jsonify({"error": "Missing username or password"}), 400

    # Accept either the username or the email address
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if user and not user.password and user.google_sub:
        return jsonify({"error": "This account signs in with Google. Use \"Continue with Google\"."}), 400
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    return _session_response(user)


@auth_bp.route('/refresh', methods=['POST'])
@limiter.limit("30/minute")
@jwt_required(refresh=True)
def refresh():
    """Trade the refresh cookie (plus its CSRF header) for a new access token; the cookie is rotated."""
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 401
    access, new_refresh = token_service.rotate(get_jwt()["jti"], user.id)
    response = jsonify({"access_token": access, "user": user.to_dict()})
    set_refresh_cookies(response, new_refresh)
    return response, 200


@auth_bp.route('/logout', methods=['POST'])
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


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user = db.session.get(User, int(get_jwt_identity()))

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.to_dict()), 200


# ---- Google sign-in (OAuth 2.0 authorization code flow with PKCE, via Authlib) ----

def _google_redirect_uri():
    return f"{current_app.config['PUBLIC_URL']}/api/auth/google/callback"


@auth_bp.route('/google/login', methods=['GET'])
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


def _unique_username(email):
    base = re.sub(r"[^a-z0-9_.]", "", email.split("@")[0].lower())[:40] or "user"
    username = base
    while User.query.filter_by(username=username).first():
        username = f"{base}{secrets.randbelow(10000):04d}"
    return username


@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    if not _google_enabled():
        return redirect("/login?error=google_disabled")

    try:
        token = oauth.google.authorize_access_token()  # validates state, PKCE and the ID token's nonce
    except OAuthError as e:
        current_app.logger.warning("Google OAuth failed: %s", e)
        return redirect("/login?error=google_failed")

    info = token.get("userinfo") or {}
    sub, email = info.get("sub"), (info.get("email") or "").lower()
    if not sub or not email or not info.get("email_verified"):
        return redirect("/login?error=google_unverified")

    link_user_id = session.pop(LINK_INTENT_KEY, None)
    existing = User.query.filter_by(google_sub=sub).first()

    if link_user_id is not None:
        user = db.session.get(User, link_user_id)
        if user is None:
            return redirect("/login?error=session_expired")
        if existing and existing.id != user.id:
            return redirect("/chat?google=already_linked")
        user.google_sub = sub
        user.avatar_url = user.avatar_url or info.get("picture")
        user.name = user.name or info.get("name")
        db.session.commit()
        return redirect("/chat?google=linked")

    user = existing
    if user is None:
        if User.query.filter_by(email=email).first():
            # Emails are not verified at sign-up, so a password account with this address may not belong
            # to this Google user. Linking must be done from inside that account instead.
            return redirect("/login?error=account_exists")
        user = User(
            username=_unique_username(email),
            email=email,
            google_sub=sub,
            name=info.get("name"),
            avatar_url=info.get("picture"),
        )
        db.session.add(user)
        db.session.commit()

    _access, refresh = token_service.issue_tokens(user.id)
    response = redirect("/auth/callback")
    set_refresh_cookies(response, refresh)
    return response
