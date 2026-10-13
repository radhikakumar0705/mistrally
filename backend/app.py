import os

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

import observability
from config import Config
from extensions import bcrypt, db, jwt, limiter, migrate, oauth

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    missing = [key for key in ("SECRET_KEY", "JWT_SECRET_KEY") if not app.config.get(key)]
    if missing:
        raise RuntimeError(
            f"{', '.join(missing)} not set. Copy backend/.env.example to backend/.env and fill it in."
        )

    observability.configure_logging(app.config["LOG_LEVEL"], app.config["LOG_FORMAT"])

    hops = app.config["PROXY_FIX_HOPS"]
    if hops:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)

    CORS(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db, directory=MIGRATIONS_DIR, render_as_batch=True)
    limiter.init_app(app)
    oauth.init_app(app)
    if app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"):
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
            overwrite=True,
        )

    _register_error_handlers(app)
    observability.init_app(app)

    from routes.auth import auth_bp
    from routes.chat import chat_bp
    from routes.documents import documents_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(documents_bp, url_prefix="/documents")

    @app.route("/")
    def home():
        return jsonify({"message": "Mistrally backend running"}), 200

    @app.route("/health/live")
    @limiter.exempt
    def live():
        return jsonify({"status": "ok"}), 200

    @app.route("/health/ready")
    @limiter.exempt
    def ready():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            app.logger.exception("Readiness check failed")
            return jsonify({"status": "unavailable", "database": "down"}), 503
        return jsonify({"status": "ok", "database": "up"}), 200

    import models  # noqa: F401  (registers every table with SQLAlchemy and Alembic)

    with app.app_context():
        observability.configure_tracing(app, db.engine)

    return app


def _register_error_handlers(app):
    # Bad or expired tokens all return 401 so the frontend can send the user back to login
    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": f"Invalid token: {reason}"}), 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify({"error": "Your session has expired. Please log in again."}), 401

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": reason}), 401

    @jwt.token_in_blocklist_loader
    def refresh_token_revoked(_header, payload):
        if payload.get("type") != "refresh":
            return False  # access tokens are short-lived and stateless
        from services.token_service import is_refresh_token_revoked

        return is_refresh_token_revoked(payload["jti"], int(payload["sub"]))

    @jwt.revoked_token_loader
    def revoked_token(_header, _payload):
        return jsonify({"error": "Your session has ended. Please log in again."}), 401

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "File is too large"}), 413

    @app.errorhandler(429)
    def rate_limited(error):
        return jsonify({"error": f"Too many requests ({error.description}). Please slow down."}), 429


if __name__ == "__main__":
    from flask_migrate import upgrade

    app = create_app()
    with app.app_context():
        upgrade()  # bring the database schema up to date before serving
    app.run(debug=app.config["DEBUG"], host="127.0.0.1", port=5000, threaded=True)
