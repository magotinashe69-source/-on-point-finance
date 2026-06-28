"""Auth tests: access control, successful login, and account lockout."""

from app.extensions import db
from app.models import User, AuditLog
from app.auth.service import MAX_FAILED_ATTEMPTS

GOOD_PASSWORD = "correct-horse-8"


def _reload(user):
    """Refresh a user from the DB after requests committed in other sessions."""
    db.session.expire_all()
    return db.session.get(User, user.id)


def test_index_redirects_to_login_when_logged_out(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_success(client, user):
    resp = client.post(
        "/login",
        data={"username": "admin", "password": GOOD_PASSWORD},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # The authenticated nav (with a Log out link) is now visible.
    assert b"Log out" in resp.data
    # A success audit row was written.
    assert AuditLog.query.filter_by(action="login").count() == 1


def test_wrong_password_shows_friendly_error(client, user):
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "nope"},
        follow_redirects=True,
    )
    assert "Wrong username or password." in resp.get_data(as_text=True)
    assert _reload(user).failed_login_attempts == 1


def test_five_wrong_passwords_lock_account(client, user):
    for _ in range(MAX_FAILED_ATTEMPTS):
        client.post("/login", data={"username": "admin", "password": "nope"})

    locked = _reload(user)
    assert locked.failed_login_attempts >= MAX_FAILED_ATTEMPTS
    assert locked.locked_until is not None

    # Even the CORRECT password is now refused with the lockout message.
    resp = client.post(
        "/login",
        data={"username": "admin", "password": GOOD_PASSWORD},
        follow_redirects=True,
    )
    assert "Account locked" in resp.get_data(as_text=True)
    # A lockout was recorded in the audit log.
    assert AuditLog.query.filter_by(action="login_locked").count() >= 1


def test_logout_requires_login_then_works(client, user):
    # Logout while anonymous redirects to the login page.
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # Log in, then log out successfully.
    client.post("/login", data={"username": "admin", "password": GOOD_PASSWORD})
    resp = client.get("/logout", follow_redirects=True)
    assert resp.status_code == 200
    assert AuditLog.query.filter_by(action="logout").count() == 1
