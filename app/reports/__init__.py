"""The 'reports' blueprint: on-screen range summary + PDF/Excel exports.

Mounted at /reports. All routes are login-required.
"""

from flask import Blueprint

bp = Blueprint("reports", __name__, url_prefix="/reports")

from app.reports import routes  # noqa: E402,F401  (import binds routes to bp)
