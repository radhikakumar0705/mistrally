from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from extensions import db, bcrypt, jwt


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    CORS(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # Bad or expired tokens all return 401 so the frontend can send the user back to login
    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": f"Invalid token: {reason}"}), 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": reason}), 401

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "File is too large"}), 413

    from routes.auth import auth_bp
    from routes.chat import chat_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/chat")

    @app.route("/")
    def home():
        return jsonify({"message": "Mistrally backend running"}), 200

    with app.app_context():
        import models  # noqa: F401  (registers every table before create_all)
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"], host="127.0.0.1", port=5000)
