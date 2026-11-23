import logging
import os
from datetime import timedelta

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

from api_blueprint.api import api
from database import DatabaseUnavailable

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app(config: dict | None = None) -> Flask:
    """App factory: gunicorn uses `main:create_app()` and the tests pass their own config."""
    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY"),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=int(os.environ.get("JWT_EXPIRES_HOURS", "8"))),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_UPLOAD_MB", "20")) * 1024 * 1024,
        UPLOAD_DIR=os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads")),
    )
    if config:
        app.config.update(config)
    if not app.config["JWT_SECRET_KEY"]:
        raise RuntimeError("Set the JWT_SECRET_KEY environment variable")

    app.json.sort_keys = False  # keeps field order (Flask 3 no longer uses JSON_SORT_KEYS)
    app.json.ensure_ascii = False  # returns accented text without escaping it

    logging.basicConfig(level=logging.INFO)
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

    jwt = JWTManager(app)

    # Token errors in the same format as the rest of the API
    @jwt.unauthorized_loader
    def _missing_token(_reason):
        return jsonify(status="error", error="missing token: send the header Authorization: Bearer <token>"), 401

    @jwt.invalid_token_loader
    def _invalid_token(_reason):
        return jsonify(status="error", error="invalid token"), 401

    @jwt.expired_token_loader
    def _expired_token(_header, _payload):
        return jsonify(status="error", error="token expired, please log in again"), 401

    @app.errorhandler(DatabaseUnavailable)
    def _database_down(_e):
        return jsonify(status="error", error="database unavailable"), 503

    @app.errorhandler(HTTPException)
    def _http(e: HTTPException):
        messages = {413: f"file larger than the {app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)} MB limit"}
        return jsonify(status="error", error=messages.get(e.code, e.description)), e.code

    @app.errorhandler(Exception)
    def _unexpected(e: Exception):
        app.logger.exception("Unhandled error: %s", e)
        return jsonify(status="error", error="internal server error"), 500

    app.register_blueprint(api)
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8080, debug=os.environ.get("FLASK_DEBUG") == "1")
