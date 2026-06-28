"""Flask extensions, created here once and shared across the whole app.

They are created *empty* and wired to the app later inside create_app().
This is the standard pattern that lets tests build their own app instance.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Database access layer. All data goes through this (no raw SQL → no SQL injection).
db = SQLAlchemy()

# Versioned schema changes (Phase 2 onwards).
migrate = Migrate()

# Logged-in sessions.
login_manager = LoginManager()

# CSRF protection for every form.
csrf = CSRFProtect()

# Brute-force defence: limits how often a route can be hit.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

# Where @login_required sends anonymous users. The 'auth' blueprint and its
# login page are built in Phase 3; the name is allowed to point ahead.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    """Tell Flask-Login how to fetch a user by id.

    Returns None for now because the User model arrives in Phase 2. Once it
    exists, this becomes:  return User.query.get(int(user_id))
    """
    return None
