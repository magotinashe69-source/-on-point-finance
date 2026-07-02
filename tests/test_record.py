"""Integration tests for the recording screen (record, validation, delete roles)."""

from datetime import date

from app.extensions import db
from app.models import Category, Transaction, User

GOOD_PASSWORD = "correct-horse-8"


def _login_admin(client):
    return client.post("/login", data={"username": "admin", "password": GOOD_PASSWORD},
                       follow_redirects=True)


def _seed_category(name, type_):
    c = Category(name=name, type=type_, is_active=True)
    db.session.add(c)
    db.session.commit()
    return c


def test_record_income_creates_entry(client, user):
    _login_admin(client)
    cat = _seed_category("Tuition", "income")
    resp = client.post(
        "/record/income",
        data={"amount": "1500.00", "category": str(cat.id), "payment_method": "Cash",
              "date": "2026-06-28", "description": "June fees"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"1,500 MT" in resp.data  # shown on the dashboard (whole meticais)
    txn = Transaction.query.one()
    assert txn.amount_cents == 150000  # 1500.00 stored as integer centavos
    assert txn.type == "income"
    assert txn.description == "June fees"


def test_zero_amount_rejected(client, user):
    _login_admin(client)
    cat = _seed_category("Tuition", "income")
    resp = client.post(
        "/record/income",
        data={"amount": "0", "category": str(cat.id), "payment_method": "Cash", "date": "2026-06-28"},
        follow_redirects=True,
    )
    assert b"greater than zero" in resp.data
    assert Transaction.query.count() == 0


def test_negative_amount_rejected(client, user):
    _login_admin(client)
    cat = _seed_category("Tuition", "income")
    client.post(
        "/record/income",
        data={"amount": "-5.00", "category": str(cat.id), "payment_method": "Cash", "date": "2026-06-28"},
        follow_redirects=True,
    )
    assert Transaction.query.count() == 0


def test_admin_can_soft_delete(client, user):
    _login_admin(client)
    cat = _seed_category("Tuition", "income")
    client.post(
        "/record/income",
        data={"amount": "100.00", "category": str(cat.id), "payment_method": "Cash", "date": "2026-06-28"},
        follow_redirects=True,
    )
    txn = Transaction.query.one()
    resp = client.post(f"/delete/{txn.id}", data={}, follow_redirects=True)
    assert resp.status_code == 200
    assert Transaction.query.count() == 1  # row kept
    assert db.session.get(Transaction, txn.id).is_deleted is True


def test_clerk_cannot_delete(client, app):
    clerk = User(name="Clerk", username="clerk", role="clerk", is_active=True)
    clerk.set_password("password-123")
    cat = Category(name="Tuition", type="income", is_active=True)
    db.session.add_all([clerk, cat])
    db.session.commit()
    txn = Transaction(date=date(2026, 6, 28), type="income", category_id=cat.id,
                      amount_cents=10000, payment_method="Cash", recorded_by=clerk.id)
    db.session.add(txn)
    db.session.commit()

    client.post("/login", data={"username": "clerk", "password": "password-123"}, follow_redirects=True)
    resp = client.post(f"/delete/{txn.id}", data={})
    assert resp.status_code == 403  # clerks are not allowed to delete
    assert db.session.get(Transaction, txn.id).is_deleted is False
