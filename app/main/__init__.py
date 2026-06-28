"""The 'main' blueprint: the everyday screens (dashboard, recording, lists).

For Phase 1 it only holds a placeholder landing page that proves the skeleton
runs. The dashboard and recording screens are built in Phase 4.
"""

from flask import Blueprint

bp = Blueprint("main", __name__)

# Import routes at the bottom so the blueprint object exists first.
from app.main import routes  # noqa: E402,F401
