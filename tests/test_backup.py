"""Tests for the database backup (VACUUM INTO) and its admin route."""

import os
import re
import sqlite3
from datetime import datetime

from app.extensions import db
from app.models import User, AuditLog
from app.admin.backup import create_backup, backup_filename

GOOD_PASSWORD = "correct-horse-8"
CLERK_PASSWORD = "clerk-password-9"


def test_backup_filename_format():
    name = backup_filename(datetime(2026, 6, 30, 14, 25, 1))
    assert name == "finance-20260630-142501.db"
    assert re.fullmatch(r"finance-\d{8}-\d{6}\.db", name)


def test_create_backup_makes_openable_copy(tmp_path):
    # Build a small source SQLite database.
    source = tmp_path / "finance.db"
    con = sqlite3.connect(source)
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, note TEXT)")
    con.execute("INSERT INTO t (note) VALUES ('hello')")
    con.commit()
    con.close()

    backups_dir = tmp_path / "backups"
    path = create_backup(str(source), str(backups_dir), datetime(2026, 6, 30, 14, 25, 1))

    # File exists with the timestamped name.
    assert os.path.exists(path)
    assert os.path.basename(path) == "finance-20260630-142501.db"

    # The copy opens and contains the same data.
    copy = sqlite3.connect(path)
    try:
        rows = copy.execute("SELECT note FROM t").fetchall()
    finally:
        copy.close()
    assert rows == [("hello",)]


def _make_clerk():
    clerk = User(name="Clerk", username="clerk", role="clerk", is_active=True)
    clerk.set_password(CLERK_PASSWORD)
    db.session.add(clerk)
    db.session.commit()
    return clerk


def _login(client, username, password):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)


def test_backup_requires_login(client):
    resp = client.post("/admin/backup", data={})
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_clerk_cannot_backup(client, app):
    _make_clerk()
    _login(client, "clerk", CLERK_PASSWORD)
    resp = client.post("/admin/backup", data={})
    assert resp.status_code == 403


def test_backup_in_memory_guard(client, user):
    """With the in-memory test DB, the route refuses gracefully (no crash)."""
    _login(client, "admin", GOOD_PASSWORD)
    resp = client.post("/admin/backup", data={}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"not available for an in-memory database" in resp.data


def test_backup_route_creates_file_and_audit(client, user, tmp_path, monkeypatch):
    """Point the route at a real file DB + temp backups dir, then back up."""
    import app.admin.routes as admin_routes

    # A real on-disk SQLite source for VACUUM INTO to copy.
    source = tmp_path / "finance.db"
    sqlite3.connect(source).close()
    backups_dir = tmp_path / "backups"
    monkeypatch.setattr(admin_routes, "BACKUPS_DIR", str(backups_dir))
    # Patch only the source-path lookup; the real session/engine stay intact
    # so the audit-row commit still works against the in-memory test DB.
    monkeypatch.setattr(admin_routes, "_source_db_path", lambda: str(source))

    _login(client, "admin", GOOD_PASSWORD)
    resp = client.post("/admin/backup", data={}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Backup saved to" in resp.data

    files = list(backups_dir.glob("finance-*.db"))
    assert len(files) == 1
    assert AuditLog.query.filter_by(action="backup").count() == 1
