"""The 'auth' blueprint: login, logout and change-password.

Routes are mounted at the app root (/login, /logout, /change-password). The
login_view in app/extensions.py points at 'auth.login'.
"""

from flask import Blueprint

bp = Blueprint("auth", __name__)

from app.auth import routes  # noqa: E402,F401  (import binds routes to bp)
