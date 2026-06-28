"""Auth routes: login, logout, change-password.

Routes stay thin; the lockout rules live in app/auth/service.py. Every login
attempt (success / failure / lockout) and every logout writes an AuditLog row.
"""

from urllib.parse import urlparse

from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db, limiter
from app.models import User
from app.audit import record_audit
from app.auth import bp
from app.auth.forms import LoginForm, ChangePasswordForm
from app.auth.service import (
    is_locked,
    register_failed_login,
    register_successful_login,
    LOCKOUT_MINUTES,
)

BAD_CREDENTIALS_MSG = "Wrong username or password."
LOCKED_MSG = f"Account locked. Try again in {LOCKOUT_MINUTES} minutes."


def _safe_next(target: str | None) -> str:
    """Only allow same-site relative redirects (no open-redirect)."""
    if target and urlparse(target).netloc == "" and target.startswith("/"):
        return target
    return url_for("main.index")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = User.query.filter_by(username=username).first()

        # Already locked: refuse before checking the password.
        if user and is_locked(user):
            record_audit("login_locked", user_id=user.id, entity="user",
                         entity_id=user.id, details={"username": username})
            db.session.commit()
            flash(LOCKED_MSG, "error")
            return render_template("auth/login.html", form=form)

        credentials_ok = bool(user) and user.is_active and user.check_password(form.password.data)

        if not credentials_ok:
            if user and user.is_active:
                register_failed_login(user)
                now_locked = is_locked(user)
                record_audit("login_failed", user_id=user.id, entity="user", entity_id=user.id,
                             details={"username": username, "failed_attempts": user.failed_login_attempts})
                db.session.commit()
                flash(LOCKED_MSG if now_locked else BAD_CREDENTIALS_MSG, "error")
            else:
                # Unknown or disabled user: log without leaking which it was.
                record_audit("login_failed",
                             user_id=user.id if user else None, entity="user",
                             entity_id=user.id if user else None,
                             details={"username": username})
                db.session.commit()
                flash(BAD_CREDENTIALS_MSG, "error")
            return render_template("auth/login.html", form=form)

        # Success.
        register_successful_login(user)
        record_audit("login", user_id=user.id, entity="user", entity_id=user.id,
                     details={"username": username})
        db.session.commit()

        login_user(user)
        session.permanent = True  # enforce the 30-minute auto-logout window
        flash(f"Welcome back, {user.name}.", "success")
        return redirect(_safe_next(request.args.get("next")))

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    record_audit("logout", user_id=current_user.id, entity="user",
                 entity_id=current_user.id, details={"username": current_user.username})
    db.session.commit()
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Your current password is not correct.", "error")
            return render_template("auth/change_password.html", form=form)

        current_user.set_password(form.new_password.data)
        record_audit("change_password", user_id=current_user.id, entity="user",
                     entity_id=current_user.id)
        db.session.commit()
        flash("Your password has been changed.", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/change_password.html", form=form)
