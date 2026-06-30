"""Tests for the 7-day chart series and its JSON route."""

from datetime import date

from app.extensions import db
from app.models import Category, Transaction, User
from app.main.services import last_7_days_series

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


def test_series_shape_and_values(app):
    end_day = date(2026, 6, 30)
    user = _seed_user()
    inc = _seed_category("Tuition", "income")
    exp = _seed_category("Rent", "expense")

    # On the end day: 1500.00 income, 400.00 expense.
    _add(end_day, "income", 150000, user.id, inc.id)
    _add(end_day, "expense", 40000, user.id, exp.id)
    # On the first day of the window (6 days earlier): 200.00 income.
    _add(date(2026, 6, 24), "income", 20000, user.id, inc.id)
    # A soft-deleted entry on the end day must NOT count.
    _add(end_day, "income", 999999, user.id, inc.id, deleted=True)
    # Outside the 7-day window (7 days before end) must NOT count.
    _add(date(2026, 6, 23), "income", 50000, user.id, inc.id)

    series = last_7_days_series(end_day)

    assert len(series["labels"]) == 7
    assert len(series["income"]) == 7
    assert len(series["expense"]) == 7
    # Values are in MAJOR MT units (centavos / 100).
    assert series["income"][0] == 200.0    # 2026-06-24, oldest in window
    assert series["income"][6] == 1500.0   # 2026-06-30, end day (deleted 9999.99 excluded)
    assert series["expense"][6] == 400.0
    # A quiet middle day is zero.
    assert series["income"][3] == 0.0
    assert series["expense"][3] == 0.0


def test_chart_route_requires_login(client):
    resp = client.get("/api/last-7-days")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_chart_route_returns_json(client, user):
    client.post("/login", data={"username": "admin", "password": GOOD_PASSWORD}, follow_redirects=True)
    resp = client.get("/api/last-7-days?date=2026-06-30")
    assert resp.status_code == 200
    assert resp.is_json
    payload = resp.get_json()
    assert set(payload.keys()) == {"labels", "income", "expense"}
    assert len(payload["labels"]) == 7
