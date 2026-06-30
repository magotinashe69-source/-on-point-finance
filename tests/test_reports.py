"""Tests for report aggregations and the PDF/Excel exports."""

from datetime import date

from app.extensions import db
from app.models import Category, Transaction, User
from app.reports.services import (
    transactions_in_range, category_breakdown, month_range,
)

GOOD_PASSWORD = "correct-horse-8"


def _seed_user():
    u = User(name="Clerk", username="clerk1", role="clerk", is_active=True)
    u.set_password("password-123")
    db.session.add(u)
    db.session.commit()
    return u


def _seed_category(name, type_):
    c = Category(name=name, type=type_, is_active=True)
    db.session.add(c)
    db.session.commit()
    return c


def _add(day, type_, cents, user_id, cat_id, deleted=False):
    db.session.add(Transaction(
        date=day, type=type_, category_id=cat_id, amount_cents=cents,
        payment_method="Cash", recorded_by=user_id, is_deleted=deleted,
    ))
    db.session.commit()


def _seed_june(app):
    user = _seed_user()
    tuition = _seed_category("Tuition", "income")
    exam = _seed_category("Exam fees", "income")
    rent = _seed_category("Rent", "expense")
    _add(date(2026, 6, 5), "income", 150000, user.id, tuition.id)
    _add(date(2026, 6, 5), "income", 50000, user.id, exam.id)
    _add(date(2026, 6, 20), "income", 100000, user.id, tuition.id)
    _add(date(2026, 6, 10), "expense", 40000, user.id, rent.id)
    _add(date(2026, 6, 10), "expense", 999999, user.id, rent.id, deleted=True)  # soft-deleted: ignore
    _add(date(2026, 5, 31), "income", 777777, user.id, tuition.id)              # out of range: ignore
    return user


def test_month_range():
    start, end = month_range(date(2026, 6, 15))
    assert start == date(2026, 6, 1)
    assert end == date(2026, 6, 30)


def test_transactions_in_range_excludes_deleted_and_out_of_range(app):
    _seed_june(app)
    rows = transactions_in_range(date(2026, 6, 1), date(2026, 6, 30))
    assert len(rows) == 4  # 3 income + 1 expense, deleted & May excluded
    assert all(not r.is_deleted for r in rows)
    # ordered oldest first
    assert rows[0].date <= rows[-1].date


def test_category_breakdown_subtotals(app):
    _seed_june(app)
    b = category_breakdown(date(2026, 6, 1), date(2026, 6, 30))
    income = dict(b["income"])
    assert income["Tuition"] == 250000   # 150000 + 100000
    assert income["Exam fees"] == 50000
    assert b["income_subtotal_cents"] == 300000
    assert dict(b["expense"])["Rent"] == 40000
    assert b["expense_subtotal_cents"] == 40000


def test_pdf_download(client, user, app):
    _seed_june(app)
    client.post("/login", data={"username": "admin", "password": GOOD_PASSWORD}, follow_redirects=True)
    resp = client.get("/reports/pdf?start=2026-06-01&end=2026-06-30")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data[:5] == b"%PDF-"
    assert "on-point-record-2026-06-01_to_2026-06-30.pdf" in resp.headers["Content-Disposition"]


def test_excel_download(client, user, app):
    _seed_june(app)
    client.post("/login", data={"username": "admin", "password": GOOD_PASSWORD}, follow_redirects=True)
    resp = client.get("/reports/excel?start=2026-06-01&end=2026-06-30")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.mimetype
    assert resp.data[:2] == b"PK"  # .xlsx is a zip archive
    assert ".xlsx" in resp.headers["Content-Disposition"]


def test_reports_require_login(client):
    for path in ("/reports/", "/reports/pdf", "/reports/excel"):
        resp = client.get(path)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
