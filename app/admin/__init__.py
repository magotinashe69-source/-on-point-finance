"""The 'admin' blueprint: users, categories and the audit log.

Mounted at /admin. EVERY route is protected by @login_required + @admin_required,
enforced on the server — hiding the nav link is not the security boundary.
"""

from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

from app.admin import routes  # noqa: E402,F401  (import binds routes to bp)
