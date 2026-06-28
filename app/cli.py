"""Flask CLI commands for On Point Finance.

  flask seed-categories   -> insert the starting income/expense categories
  flask create-admin      -> interactively create the first admin user

Both are registered on the app in the application factory.
"""

import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import User, Category

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


def register_cli(app) -> None:
    """Attach the CLI commands to the Flask app (called from the factory)."""
    app.cli.add_command(seed_categories)
    app.cli.add_command(create_admin)
