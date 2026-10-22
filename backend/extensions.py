from authlib.integrations.flask_client import OAuth
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)
oauth = OAuth()


def user_or_ip():
    """Rate-limit key: the logged-in user when there is one, otherwise the client IP."""
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
    except Exception:
        identity = None
    return f"user:{identity}" if identity else get_remote_address()
