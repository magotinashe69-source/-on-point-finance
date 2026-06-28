"""Configuration for On Point Finance.

Everything sensitive (the SECRET_KEY, the database location) is read from the
environment, never written into code. Copy .env.example to .env and fill it in.
"""

import os
from datetime import timedelta

from sqlalchemy.pool import StaticPool

# Absolute path to the project root (the folder this file lives in).
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared by every environment."""

    # --- Security: the key that signs login/session cookies. ---
    # MUST come from the environment. If it is missing the app refuses to start
    # (see app/__init__.py) so we never run with an insecure or shared key.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # --- Database: one SQLite file inside the instance/ folder. ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(basedir, "instance", "finance.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Session cookie hardening ---
    SESSION_COOKIE_HTTPONLY = True        # JavaScript cannot read the cookie
    SESSION_COOKIE_SAMESITE = "Lax"       # blocks most cross-site cookie sending
    SESSION_COOKIE_SECURE = False         # set True ONLY if you ever serve over HTTPS;
    #                                       we run on localhost (http), so it stays False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)   # auto-logout after 30 min idle

    # --- Rate-limiter storage. In-memory is fine for a single office PC. ---
    RATELIMIT_STORAGE_URI = "memory://"

    @staticmethod
    def init_app(app):
        """Hook for per-environment setup. Nothing needed yet."""
        pass


class DevConfig(Config):
    """Used while you are building. Debug on, friendlier errors."""
    DEBUG = True


class ProdConfig(Config):
    """Used for the real desktop app (served by waitress in Phase 9)."""
    DEBUG = False


class TestConfig(Config):
    """Used by pytest. Hermetic: in-memory DB, no CSRF tokens, no rate limiting."""
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-secret-key-not-for-production"
    # In-memory SQLite shared across connections via a single static connection.
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    WTF_CSRF_ENABLED = False   # tests post forms without a CSRF token
    RATELIMIT_ENABLED = False  # don't 429 the rapid login attempts in tests


# Look up a config class by name (set FLASK_CONFIG in .env).
config = {
    "dev": DevConfig,
    "prod": ProdConfig,
    "test": TestConfig,
    "default": DevConfig,
}
