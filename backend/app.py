from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from extensions import db, bcrypt, jwt


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)


    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    from routes.auth import auth_bp
    from routes.chat import chat_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/chat")

    @app.route("/")
    def home():
        return jsonify({"message": "Mistrally backend running"}), 200

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="127.0.0.1", port=5000)
