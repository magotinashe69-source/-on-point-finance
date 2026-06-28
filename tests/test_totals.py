"""Tests for the daily totals math and the soft-delete rule."""

from datetime import date

from app.extensions import db
from app.models import Category, Transaction, User
from app.main.services import compute_totals, transactions_on


class _FakeEntry:
    """Minimal stand-in so the pure totals function can be tested without a DB."""

    def __init__(self, type_, amount_cents):
        self.type = type_
        self.amount_cents = amount_cents


def test_compute_totals_pure():
    entries = [
        _FakeEntry("income", 150000),
        _FakeEntry("income", 50000),
        _FakeEntry("expense", 30000),
    ]
    totals = compute_totals(entries)
    assert totals["income_cents"] == 200000
    assert totals["expense_cents"] == 30000
    assert totals["balance_cents"] == 170000


def test_compute_totals_empty():
    assert compute_totals([]) == {"income_cents": 0, "expense_cents": 0, "balance_cents": 0}


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


def test_soft_deleted_excluded_from_totals_but_kept(app):
    day = date(2026, 6, 28)
    user = _seed_user()
    income_cat = _seed_category("Tuition", "income")
    expense_cat = _seed_category("Rent", "expense")

    t1 = Transaction(date=day, type="income", category_id=income_cat.id,
                     amount_cents=150000, payment_method="Cash", recorded_by=user.id)
    t2 = Transaction(date=day, type="expense", category_id=expense_cat.id,
                     amount_cents=40000, payment_method="Bank", recorded_by=user.id)
    db.session.add_all([t1, t2])
    db.session.commit()

    totals = compute_totals(transactions_on(day))
    assert totals == {"income_cents": 150000, "expense_cents": 40000, "balance_cents": 110000}

    # Soft-delete the income entry.
    t1.is_deleted = True
    db.session.commit()

    totals_after = compute_totals(transactions_on(day))
    assert totals_after == {"income_cents": 0, "expense_cents": 40000, "balance_cents": -40000}

    # The row is STILL in the database (soft delete) — just flagged and hidden.
    assert Transaction.query.count() == 2
    assert db.session.get(Transaction, t1.id).is_deleted is True
    assert transactions_on(day) == [t2]
