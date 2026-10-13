from datetime import datetime

from extensions import bcrypt, db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)  # None for accounts that only sign in with Google
    google_sub = db.Column(db.String(255), unique=True, nullable=True)
    name = db.Column(db.String(120), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bool(self.password) and bcrypt.check_password_hash(self.password, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "has_password": bool(self.password),
            "google_linked": bool(self.google_sub),
        }
