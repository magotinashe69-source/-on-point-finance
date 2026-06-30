"""Admin routes. Every route requires login AND the admin role (server-enforced)."""

import os
from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user

from config import basedir
from app.extensions import db
from app.models import User, Category, AuditLog
from app.audit import record_audit
from app.auth.decorators import admin_required
from app.auth.service import is_locked
from app.admin import bp
from app.admin.forms import AddUserForm, AddCategoryForm, ActionForm
from app.admin.backup import create_backup

AUDIT_PER_PAGE = 20
BACKUPS_DIR = os.path.join(basedir, "backups")


def _flash_form_errors(form) -> None:
    """Surface the first validation error per field as a friendly flash."""
    for errors in form.errors.values():
        for error in errors:
            flash(error, "error")


def _source_db_path() -> str:
    """Filesystem path of the live SQLite database (empty for in-memory)."""
    return db.engine.url.database or ""


@bp.route("/")
@login_required
@admin_required
def index():
    return redirect(url_for("admin.users"))


# --- Users -----------------------------------------------------------------

@bp.route("/users")
@login_required
@admin_required
def users():
    people = User.query.order_by(User.name).all()
    return render_template(
        "admin/users.html",
        users=people, form=AddUserForm(), action=ActionForm(), is_locked=is_locked,
    )


@bp.route("/users/add", methods=["POST"])
@login_required
@admin_required
def add_user():
    form = AddUserForm()
    if not form.validate_on_submit():
        _flash_form_errors(form)
        return redirect(url_for("admin.users"))

    username = form.username.data.strip()
    if User.query.filter_by(username=username).first():
        flash(f"A user named '{username}' already exists.", "error")
        return redirect(url_for("admin.users"))

    user = User(name=form.name.data.strip(), username=username, role=form.role.data, is_active=True)
    user.set_password(form.password.data)
    db.session.add(user)
    db.session.flush()
    record_audit("create_user", user_id=current_user.id, entity="user", entity_id=user.id,
                 details={"username": username, "role": user.role})
    db.session.commit()
    flash(f"User '{username}' created.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_user_active(user_id: int):
    if not ActionForm().validate_on_submit():
        abort(400)

    user = db.session.get(User, user_id)
    if user is None:
        flash("That user was not found.", "warning")
        return redirect(url_for("admin.users"))

    # Never let an admin lock themselves out of their own account.
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("admin.users"))

    user.is_active = not user.is_active
    record_audit("toggle_user_active", user_id=current_user.id, entity="user", entity_id=user.id,
                 details={"username": user.username, "is_active": user.is_active})
    db.session.commit()
    flash(f"User '{user.username}' is now {'active' if user.is_active else 'inactive'}.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/unlock", methods=["POST"])
@login_required
@admin_required
def unlock_user(user_id: int):
    if not ActionForm().validate_on_submit():
        abort(400)

    user = db.session.get(User, user_id)
    if user is None:
        flash("That user was not found.", "warning")
        return redirect(url_for("admin.users"))

    user.locked_until = None
    user.failed_login_attempts = 0
    record_audit("unlock_user", user_id=current_user.id, entity="user", entity_id=user.id,
                 details={"username": user.username})
    db.session.commit()
    flash(f"User '{user.username}' has been unlocked.", "success")
    return redirect(url_for("admin.users"))


# --- Backup ----------------------------------------------------------------

@bp.route("/backup", methods=["POST"])
@login_required
@admin_required
def backup():
    if not ActionForm().validate_on_submit():
        abort(400)

    source = _source_db_path()
    if not source or source == ":memory:":
        flash("Backup is not available for an in-memory database.", "error")
        return redirect(url_for("admin.users"))

    try:
        path = create_backup(source, BACKUPS_DIR, datetime.now())
    except Exception:  # noqa: BLE001 — show a friendly message, never a stack trace
        current_app.logger.exception("Database backup failed")
        flash("Sorry, the backup could not be created. Please try again.", "error")
        return redirect(url_for("admin.users"))

    record_audit("backup", user_id=current_user.id, entity="database",
                 details={"file": os.path.basename(path)})
    db.session.commit()
    flash(f"Backup saved to {path}", "success")
    return redirect(url_for("admin.users"))


# --- Categories ------------------------------------------------------------

@bp.route("/categories")
@login_required
@admin_required
def categories():
    cats = Category.query.order_by(Category.type, Category.name).all()
    return render_template(
        "admin/categories.html",
        categories=cats, form=AddCategoryForm(), action=ActionForm(),
    )


@bp.route("/categories/add", methods=["POST"])
@login_required
@admin_required
def add_category():
    form = AddCategoryForm()
    if not form.validate_on_submit():
        _flash_form_errors(form)
        return redirect(url_for("admin.categories"))

    name = form.name.data.strip()
    cat_type = form.type.data
    if Category.query.filter_by(name=name, type=cat_type).first():
        flash(f"A {cat_type} category named '{name}' already exists.", "error")
        return redirect(url_for("admin.categories"))

    category = Category(name=name, type=cat_type, is_active=True)
    db.session.add(category)
    db.session.flush()
    record_audit("create_category", user_id=current_user.id, entity="category", entity_id=category.id,
                 details={"name": name, "type": cat_type})
    db.session.commit()
    flash(f"Category '{name}' added.", "success")
    return redirect(url_for("admin.categories"))


@bp.route("/categories/<int:category_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_category_active(category_id: int):
    if not ActionForm().validate_on_submit():
        abort(400)

    category = db.session.get(Category, category_id)
    if category is None:
        flash("That category was not found.", "warning")
        return redirect(url_for("admin.categories"))

    category.is_active = not category.is_active  # hide/show — never hard delete
    record_audit("toggle_category_active", user_id=current_user.id, entity="category", entity_id=category.id,
                 details={"name": category.name, "type": category.type, "is_active": category.is_active})
    db.session.commit()
    flash(f"Category '{category.name}' is now {'visible' if category.is_active else 'hidden'}.", "success")
    return redirect(url_for("admin.categories"))


# --- Audit log -------------------------------------------------------------

@bp.route("/audit")
@login_required
@admin_required
def audit():
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        db.select(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()),
        page=page, per_page=AUDIT_PER_PAGE, error_out=False,
    )
    user_names = {u.id: u.username for u in User.query.all()}
    return render_template("admin/audit.html", pagination=pagination, user_names=user_names)
