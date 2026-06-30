"""Admin-area tests: role enforcement and admin actions."""

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import User, Category, AuditLog


def _naive_utc_in(minutes):
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=minutes)

GOOD_PASSWORD = "correct-horse-8"
CLERK_PASSWORD = "clerk-password-9"

ADMIN_URLS = ["/admin/", "/admin/users", "/admin/categories", "/admin/audit"]


def _make_clerk(username="clerk"):
    clerk = User(name="Clerk Person", username=username, role="clerk", is_active=True)
    clerk.set_password(CLERK_PASSWORD)
    db.session.add(clerk)
    db.session.commit()
    return clerk


def _login(client, username, password):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)


def test_clerk_gets_403_on_admin_urls(client, app):
    _make_clerk()
    _login(client, "clerk", CLERK_PASSWORD)
    for url in ADMIN_URLS:
        resp = client.get(url)
        assert resp.status_code == 403, f"{url} should be forbidden for a clerk"


def test_anonymous_redirected_to_login(client):
    resp = client.get("/admin/users")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_admin_can_add_user(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    resp = client.post("/admin/users/add", data={
        "name": "New Clerk", "username": "newclerk", "password": "long-enough-1", "role": "clerk",
    }, follow_redirects=True)
    assert resp.status_code == 200
    created = User.query.filter_by(username="newclerk").one()
    assert created.role == "clerk"
    assert created.password_hash and created.password_hash != "long-enough-1"  # hashed
    assert AuditLog.query.filter_by(action="create_user").count() == 1


def test_admin_cannot_deactivate_self(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    me = User.query.filter_by(username="admin").one()
    resp = client.post(f"/admin/users/{me.id}/toggle-active", data={}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"cannot deactivate your own account" in resp.data
    assert db.session.get(User, me.id).is_active is True


def test_admin_can_deactivate_and_reactivate_other(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    clerk = _make_clerk()
    client.post(f"/admin/users/{clerk.id}/toggle-active", data={}, follow_redirects=True)
    assert db.session.get(User, clerk.id).is_active is False
    client.post(f"/admin/users/{clerk.id}/toggle-active", data={}, follow_redirects=True)
    assert db.session.get(User, clerk.id).is_active is True


def test_unlock_clears_lockout(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    clerk = _make_clerk()
    clerk.failed_login_attempts = 5
    clerk.locked_until = _naive_utc_in(15)
    db.session.commit()

    client.post(f"/admin/users/{clerk.id}/unlock", data={}, follow_redirects=True)
    refreshed = db.session.get(User, clerk.id)
    assert refreshed.locked_until is None
    assert refreshed.failed_login_attempts == 0


def test_add_and_toggle_category(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    client.post("/admin/categories/add", data={"name": "Library fees", "type": "income"},
                follow_redirects=True)
    cat = Category.query.filter_by(name="Library fees", type="income").one()
    assert cat.is_active is True

    client.post(f"/admin/categories/{cat.id}/toggle-active", data={}, follow_redirects=True)
    assert db.session.get(Category, cat.id).is_active is False
    # Row still exists — hidden, never hard-deleted.
    assert Category.query.filter_by(name="Library fees").count() == 1
    assert AuditLog.query.filter_by(action="create_category").count() == 1
