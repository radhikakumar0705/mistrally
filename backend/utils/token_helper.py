import datetime
import jwt
from functools import wraps
from flask import request, jsonify, current_app
from models.user import User

def create_access_token(user_id):
    """Generate JWT token for a user."""
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    return token

def decode_access_token(token):
    """Decode a JWT token."""
    try:
        return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    """Decorator for protecting routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]  # Bearer <token>

        if not token:
            return jsonify({"error": "Token missing"}), 401

        payload = decode_access_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        user = User.query.get(payload["user_id"])
        if not user:
            return jsonify({"error": "User not found"}), 404

        return f(user, *args, **kwargs)
    return decorated
