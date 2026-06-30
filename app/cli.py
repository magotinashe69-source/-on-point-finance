"""Flask CLI commands for On Point Finance.

  flask seed-categories   -> insert the starting income/expense categories
  flask create-admin      -> interactively create the first admin user
  flask reset-password    -> set a new password for a user (and unlock them)
  flask change-login      -> rename a user, set a new password, and unlock them
  flask force-reset-admin -> non-interactive reset via env vars (for deploy hooks)

All are registered on the app in the application factory.
"""

import os

import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import User, Category
from app.audit import record_audit

# Starting categories from SPEC.md section 4.
INCOME_CATEGORIES = [
    "Tuition", "Registration", "Exam fees", "Uniforms", "Transport", "Donations",
]
EXPENSE_CATEGORIES = [
    "Salaries", "Rent", "Electricity", "Internet", "Materials",
    "Maintenance", "Cleaning", "Cambridge fees",
]


@click.command("seed-categories")
@with_appcontext
def seed_categories():
    """Insert the starting categories. Safe to run more than once."""
    created = 0
    for cat_type, names in (("income", INCOME_CATEGORIES), ("expense", EXPENSE_CATEGORIES)):
        for name in names:
            exists = Category.query.filter_by(name=name, type=cat_type).first()
            if not exists:
                db.session.add(Category(name=name, type=cat_type, is_active=True))
                created += 1
    db.session.commit()
    click.echo(f"Seed complete. Added {created} new categor{'y' if created == 1 else 'ies'}.")


@click.command("create-admin")
@with_appcontext
def create_admin():
    """Interactively create an admin user (password is hashed, never stored plain)."""
    name = click.prompt("Full name").strip()
    username = click.prompt("Username").strip()

    if not name or not username:
        raise click.ClickException("Name and username are required.")
    if User.query.filter_by(username=username).first():
        raise click.ClickException(f"A user named '{username}' already exists.")

    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")

    user = User(name=name, username=username, role="admin", is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Admin user '{username}' created.")


@click.command("reset-password")
@click.argument("username")
@with_appcontext
def reset_password(username):
    """Set a new password for USERNAME and unlock the account."""
    user = User.query.filter_by(username=username).first()
    if user is None:
        raise click.ClickException(f"No user named '{username}' was found.")

    password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")

    user.set_password(password)
    # Unlock the account at the same time.
    user.locked_until = None
    user.failed_login_attempts = 0

    record_audit("reset_password", user_id=user.id, entity="user", entity_id=user.id,
                 details={"username": user.username, "via": "cli"})
    db.session.commit()
    click.echo(f"Password updated for {username}")


@click.command("change-login")
@click.argument("old_username")
@click.argument("new_username")
@with_appcontext
def change_login(old_username, new_username):
    """Rename OLD_USERNAME to NEW_USERNAME, set a new password, and unlock."""
    user = User.query.filter_by(username=old_username).first()
    if user is None:
        raise click.ClickException(f"No user named '{old_username}' was found.")

    new_username = new_username.strip()
    if not new_username:
        raise click.ClickException("The new username cannot be empty.")

    # Allow renaming to the same user (acts as a password reset), but block
    # collisions with a DIFFERENT existing account.
    clash = User.query.filter_by(username=new_username).first()
    if clash is not None and clash.id != user.id:
        raise click.ClickException(f"A user named '{new_username}' already exists.")

    password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")

    user.username = new_username
    user.set_password(password)
    # Unlock the account at the same time.
    user.locked_until = None
    user.failed_login_attempts = 0

    record_audit("change_login", user_id=user.id, entity="user", entity_id=user.id,
                 details={"old_username": old_username, "new_username": new_username, "via": "cli"})
    db.session.commit()
    click.echo(f"Login updated: '{old_username}' is now '{new_username}' (password reset, account unlocked).")


@click.command("force-reset-admin")
@with_appcontext
def force_reset_admin():
    """One-time, non-interactive password reset driven by environment variables.

    Reads RESET_USERNAME and RESET_PASSWORD. Intended for hosts with no shell
    access: set both env vars for a single deploy, then remove them. Safe to
    leave wired into build.sh — it does nothing unless both vars are set, and it
    exits successfully on every path so it never breaks a deploy. Never prints
    the password.
    """
    username = (os.environ.get("RESET_USERNAME") or "").strip()
    password = os.environ.get("RESET_PASSWORD") or ""

    if not username or not password:
        click.echo("force-reset-admin: no reset requested, skipping.")
        return

    user = User.query.filter_by(username=username).first()
    if user is None:
        click.echo(f"force-reset-admin: no user named '{username}', skipping.")
        return

    user.set_password(password)
    # Unlock the account at the same time.
    user.locked_until = None
    user.failed_login_attempts = 0

    record_audit("force_reset_admin", user_id=user.id, entity="user", entity_id=user.id,
                 details={"username": user.username, "via": "deploy-env"})
    db.session.commit()
    click.echo(f"force-reset-admin: password updated for {username}")


def register_cli(app) -> None:
    """Attach the CLI commands to the Flask app (called from the factory)."""
    app.cli.add_command(seed_categories)
    app.cli.add_command(create_admin)
    app.cli.add_command(reset_password)
    app.cli.add_command(change_login)
    app.cli.add_command(force_reset_admin)
