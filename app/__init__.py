"""Application factory for On Point Finance.

create_app() builds and returns a fully wired Flask app. Building the app inside
a function (rather than at import time) means run.py, the flask CLI, and the test
suite can each create their own copy with the right configuration.
"""

import os

from flask import Flask

from config import config
from app.extensions import db, migrate, login_manager, csrf, limiter


def create_app(config_name=None):
    # Pick the configuration: argument > FLASK_CONFIG env var > "default" (dev).
    config_name = config_name or os.environ.get("FLASK_CONFIG", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    # Refuse to start without a signing key. This is deliberate: a missing key
    # means insecure sessions, so we fail loudly with a helpful message instead.
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY is not set.\n"
            "Copy .env.example to .env and set a strong key. Generate one with:\n"
            '  python -c "import secrets; print(secrets.token_hex(32))"'
        )

    # Ensure the instance/ folder exists for the SQLite database file.
    os.makedirs(app.instance_path, exist_ok=True)

    # Wire the extensions to this app.
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Register blueprints (feature areas). More are added in later phases:
    #   auth (Phase 3), reports (Phase 6), admin (Phase 7).
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    return app
