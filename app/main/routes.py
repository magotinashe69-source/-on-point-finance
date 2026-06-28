"""Routes for the main blueprint."""

from flask import render_template
from flask_login import login_required

from app.main import bp


@bp.route("/")
@login_required
def index():
    # Protected: anonymous users are redirected to auth.login (login_view).
    return render_template("main/index.html")
