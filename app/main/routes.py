"""Routes for the main blueprint."""

from flask import render_template

from app.main import bp


@bp.route("/")
def index():
    # In Phase 3, once the auth system exists, this gets protected with
    # @login_required so the dashboard is never reachable without logging in.
    return render_template("main/index.html")
