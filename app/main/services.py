"""Business logic for the recording screen — plain, testable functions.

Totals are computed in centavos (integers). Formatting to "1,500.00 MT" happens
only at the template edge via cents_to_str.
"""

from datetime import date, timedelta
from typing import Iterable

from sqlalchemy import func

from app.extensions import db
from app.models import Transaction
from app.money import cents_to_major


def compute_totals(entries: Iterable) -> dict[str, int]:
    """Sum income, expense and balance (in centavos) for the given entries.

    Pure: takes any iterable of objects with .type and .amount_cents, so it can
    be tested without a database.
    """
    income = sum(e.amount_cents for e in entries if e.type == "income")
    expense = sum(e.amount_cents for e in entries if e.type == "expense")
    return {
        "income_cents": income,
        "expense_cents": expense,
        "balance_cents": income - expense,
    }


def transactions_on(day: date) -> list[Transaction]:
    """Non-deleted transactions for a single day, newest first."""
    return (
        Transaction.query
        .filter(Transaction.date == day, Transaction.is_deleted.is_(False))
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .all()
    )


def daily_totals_cents(start_day: date, end_day: date) -> dict[tuple[date, str], int]:
    """Sum amount_cents per (day, type) over an inclusive date range.

    One grouped ORM query (no raw SQL). Excludes soft-deleted rows.
    """
    rows = (
        db.session.query(
            Transaction.date,
            Transaction.type,
            func.sum(Transaction.amount_cents),
        )
        .filter(
            Transaction.is_deleted.is_(False),
            Transaction.date >= start_day,
            Transaction.date <= end_day,
        )
        .group_by(Transaction.date, Transaction.type)
        .all()
    )
    return {(row_date, row_type): int(total or 0) for row_date, row_type, total in rows}


def last_7_days_series(end_day: date) -> dict[str, list]:
    """Labels + income/expense arrays for the 7 days ending on `end_day`.

    Values are in major MT units (for the chart). Days with no entries are 0.
    """
    days = [end_day - timedelta(days=offset) for offset in range(6, -1, -1)]  # oldest -> end_day
    totals = daily_totals_cents(days[0], days[-1])
    return {
        "labels": [d.strftime("%a %d") for d in days],
        "income": [cents_to_major(totals.get((d, "income"), 0)) for d in days],
        "expense": [cents_to_major(totals.get((d, "expense"), 0)) for d in days],
    }
