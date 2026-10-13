"""Issue, rotate and revoke refresh tokens (stored server-side so they can be revoked)."""
from datetime import UTC, datetime

from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token

from extensions import db
from models.refresh_token import RefreshToken


def _naive_utc(timestamp):
    return datetime.fromtimestamp(timestamp, UTC).replace(tzinfo=None)


def issue_tokens(user_id):
    """New access + refresh token pair; the refresh token is recorded so it can be rotated or revoked."""
    identity = str(user_id)
    access = create_access_token(identity=identity)
    refresh = create_refresh_token(identity=identity)
    claims = decode_token(refresh)
    db.session.add(RefreshToken(jti=claims["jti"], user_id=user_id, expires_at=_naive_utc(claims["exp"])))
    db.session.commit()
    return access, refresh


def rotate(jti, user_id):
    """Exchange a valid refresh token for a new pair and revoke the old one."""
    access, refresh = issue_tokens(user_id)
    old = RefreshToken.query.filter_by(jti=jti).first()
    old.revoked_at = datetime.utcnow()
    old.replaced_by = decode_token(refresh)["jti"]
    db.session.commit()
    return access, refresh


def revoke(jti):
    token = RefreshToken.query.filter_by(jti=jti).first()
    if token and token.revoked_at is None:
        token.revoked_at = datetime.utcnow()
        db.session.commit()


def revoke_all(user_id):
    RefreshToken.query.filter_by(user_id=user_id, revoked_at=None).update({"revoked_at": datetime.utcnow()})
    db.session.commit()


def is_refresh_token_revoked(jti, user_id):
    """
    Blocklist check for refresh tokens. Unknown or expired tokens are rejected. A token that was
    already rotated is being replayed, which means it leaked: revoke every token the user has.
    """
    token = RefreshToken.query.filter_by(jti=jti).first()
    if token is None or token.expires_at <= datetime.utcnow():
        return True
    if token.revoked_at is not None:
        if token.replaced_by:
            current_app.logger.warning("Refresh token reuse detected for user %s; revoking all sessions", user_id)
            revoke_all(user_id)
        return True
    return False
