import os

from flask import Flask

from .security import install_security


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25MB
    app.config["UPLOAD_EXTENSIONS"] = {".csv"}
    app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

    from .routes import bp as routes_bp

    app.register_blueprint(routes_bp)
    install_security(app)
    return app

