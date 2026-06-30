"""Report queries and aggregations — plain, testable functions.

All queries use SQLAlchemy (no raw SQL) and exclude soft-deleted rows.
Money stays in integer centavos; formatting happens at the edge.
"""

import calendar
from datetime import date

from sqlalchemy import func

from app.extensions import db
from app.models import Transaction, Category


def month_range(today: date) -> tuple[date, date]:
    """First and last day of the month containing `today`."""
    start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    return start, today.replace(day=last_day)


def transactions_in_range(start_day: date, end_day: date) -> list[Transaction]:
    """Non-deleted transactions in an inclusive date range, oldest first."""
    return (
        Transaction.query
        .filter(
            Transaction.is_deleted.is_(False),
            Transaction.date >= start_day,
            Transaction.date <= end_day,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )


def category_breakdown(start_day: date, end_day: date) -> dict:
    """Totals (in centavos) grouped by category, split into income and expense.

    Returns {"income": [(name, cents), ...], "expense": [...],
             "income_subtotal_cents": int, "expense_subtotal_cents": int}.
    """
    rows = (
        db.session.query(
            Category.type,
            Category.name,
            func.sum(Transaction.amount_cents),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.is_deleted.is_(False),
            Transaction.date >= start_day,
            Transaction.date <= end_day,
        )
        .group_by(Category.type, Category.name)
        .order_by(Category.type, Category.name)
        .all()
    )

    income = [(name, int(total)) for type_, name, total in rows if type_ == "income"]
    expense = [(name, int(total)) for type_, name, total in rows if type_ == "expense"]
    return {
        "income": income,
        "expense": expense,
        "income_subtotal_cents": sum(c for _, c in income),
        "expense_subtotal_cents": sum(c for _, c in expense),
    }
