"""Business logic for the recording screen — plain, testable functions.

Totals are computed in centavos (integers). Formatting to "1,500.00 MT" happens
only at the template edge via cents_to_str.
"""

from datetime import date
from typing import Iterable

from app.models import Transaction


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
