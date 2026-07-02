"""Student records tests (Stage 1): add a student, search, and CSV import."""

import io

from app.extensions import db
from app.models import Student, AuditLog
from app.students.services import import_students_from_csv

GOOD_PASSWORD = "correct-horse-8"
CLERK_PASSWORD = "clerk-password-9"


def _login(client, username, password):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)


def _make_clerk(username="clerk"):
    from app.models import User
    clerk = User(name="Clerk Person", username=username, role="clerk", is_active=True)
    clerk.set_password(CLERK_PASSWORD)
    db.session.add(clerk)
    db.session.commit()
    return clerk


# --- Adding a student -------------------------------------------------------

def test_add_student_works(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    resp = client.post("/students/add", data={
        "full_name": "Ana Muianga",
        "class_name": "Grade 5",
        "guardian_phone": "840000000",
    }, follow_redirects=True)
    assert resp.status_code == 200

    created = Student.query.filter_by(full_name="Ana Muianga").one()
    assert created.class_name == "Grade 5"
    assert created.guardian_phone == "840000000"
    assert created.is_active is True
    # Optional blanks stored as NULL, not empty strings.
    assert created.guardian_name is None
    # One audit row for the create.
    assert AuditLog.query.filter_by(action="create_student").count() == 1


def test_add_student_requires_full_name(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    client.post("/students/add", data={"full_name": "   "}, follow_redirects=True)
    assert Student.query.count() == 0


def test_search_filters_the_list(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    db.session.add_all([
        Student(full_name="Ana Muianga", class_name="Grade 5", is_active=True),
        Student(full_name="Bruno Sitoe", class_name="Grade 6", is_active=True),
    ])
    db.session.commit()

    resp = client.get("/students/?q=Ana")
    assert b"Ana Muianga" in resp.data
    assert b"Bruno Sitoe" not in resp.data


# --- Deactivate (admin only) ------------------------------------------------

def test_admin_can_deactivate_student(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    s = Student(full_name="Carla Nhaca", is_active=True)
    db.session.add(s)
    db.session.commit()

    client.post(f"/students/{s.id}/deactivate", data={}, follow_redirects=True)
    refreshed = db.session.get(Student, s.id)
    assert refreshed.is_active is False           # soft state
    assert Student.query.count() == 1             # never hard deleted
    assert AuditLog.query.filter_by(action="deactivate_student").count() == 1


def test_clerk_cannot_deactivate_student(client, user):
    _make_clerk()
    _login(client, "clerk", CLERK_PASSWORD)
    s = Student(full_name="Dino Cossa", is_active=True)
    db.session.add(s)
    db.session.commit()

    resp = client.post(f"/students/{s.id}/deactivate", data={})
    assert resp.status_code == 403
    assert db.session.get(Student, s.id).is_active is True


# --- CSV import -------------------------------------------------------------

CSV_TEXT = (
    "full_name,class_name,guardian_name,guardian_phone,student_no\n"
    "Ana Muianga,Grade 5,Maria Muianga,840000001,S001\n"
    "Bruno Sitoe,Grade 6,Jose Sitoe,840000002,S002\n"
    ",,,,\n"                                       # blank row -> skipped
    ",Grade 7,No Name Guardian,840000003,S003\n"   # missing full_name -> skipped
    "Ana Muianga,Grade 5,Maria Muianga,840000001,S001\n"  # duplicate in file -> skipped
)


def test_import_adds_and_skips(app):
    # Runs the pure service against the in-memory DB inside the app context.
    summary = import_students_from_csv(CSV_TEXT)
    db.session.commit()

    assert summary.added == 2
    assert summary.skipped_blank == 1
    assert summary.skipped_no_name == 1
    assert summary.skipped_duplicate == 1
    assert summary.skipped_total == 3
    assert Student.query.count() == 2


def test_import_skips_existing_on_reupload(app):
    # First import inserts two.
    import_students_from_csv(CSV_TEXT)
    db.session.commit()
    assert Student.query.count() == 2

    # Re-uploading the same file adds nothing (same name + class already exist).
    summary = import_students_from_csv(CSV_TEXT)
    db.session.commit()
    assert summary.added == 0
    # Ana + Bruno already in the DB, plus the in-file repeat of Ana = 3.
    assert summary.skipped_duplicate == 3
    assert Student.query.count() == 2


def test_import_route_writes_one_audit_row(client, user):
    _login(client, "admin", GOOD_PASSWORD)
    data = {"file": (io.BytesIO(CSV_TEXT.encode("utf-8")), "students.csv")}
    resp = client.post("/students/import", data=data,
                       content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    assert Student.query.count() == 2
    assert AuditLog.query.filter_by(action="import_students").count() == 1


def test_import_page_is_admin_only(client, user):
    _make_clerk()
    _login(client, "clerk", CLERK_PASSWORD)
    assert client.get("/students/import").status_code == 403
