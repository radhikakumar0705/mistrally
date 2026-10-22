from datetime import datetime

from extensions import db


class RefreshToken(db.Model):
    """
    One row per issued refresh token. Tokens are rotated on every use: the old row is revoked and
    points at its replacement. Presenting a revoked token means it was stolen or replayed, so the
    whole family of the user's tokens is revoked.
    """

    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    replaced_by = db.Column(db.String(64), nullable=True)

    @property
    def active(self):
        return self.revoked_at is None and self.expires_at > datetime.utcnow()
