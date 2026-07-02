"""The 'students' blueprint: the student records screens.

Stage 1 covers listing/searching, adding one student, deactivating (admin only),
and bulk CSV import (admin only). Fees and payments come in a later stage.
"""

from flask import Blueprint

bp = Blueprint("students", __name__, url_prefix="/students")

# Import routes at the bottom so the blueprint object exists first.
from app.students import routes  # noqa: E402,F401
