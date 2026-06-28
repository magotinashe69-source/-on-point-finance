"""Shared pytest fixtures: a test app, a client, and a known user."""

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import User


@pytest.fixture
def app():
    app = create_app("test")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    """A known, active admin user: admin / correct-horse-8."""
    u = User(name="Test Admin", username="admin", role="admin", is_active=True)
    u.set_password("correct-horse-8")
    _db.session.add(u)
    _db.session.commit()
    return u
