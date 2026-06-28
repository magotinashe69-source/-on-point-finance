"""Authorisation decorators.

admin_required is used from Phase 7 onward for admin-only routes. It is defined
now so the rule lives in one place.
"""

from functools import wraps
from typing import Callable

from flask import abort
from flask_login import current_user

from app.extensions import login_manager


def admin_required(view: Callable) -> Callable:
    """Allow only logged-in admins. Anonymous users go to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if getattr(current_user, "role", None) != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped
