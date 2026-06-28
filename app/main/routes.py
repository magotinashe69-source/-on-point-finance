"""Routes for the main blueprint: dashboard, record entry, soft delete."""

from datetime import date, datetime

from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Category, Transaction
from app.money import cents_to_str
from app.audit import record_audit
from app.auth.decorators import admin_required
from app.main import bp
from app.main.forms import TransactionForm, DeleteForm
from app.main.services import compute_totals, transactions_on


def _parse_day(raw: str | None) -> date:
    """Parse a YYYY-MM-DD string, defaulting to today on missing/invalid input."""
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()


@bp.route("/")
@login_required
def index():
    selected_day = _parse_day(request.args.get("date"))
    entries = transactions_on(selected_day)
    totals = compute_totals(entries)
    return render_template(
        "main/index.html",
        selected_day=selected_day,
        entries=entries,
        totals=totals,
        delete_form=DeleteForm(),
    )


@bp.route("/record/<txn_type>", methods=["GET", "POST"])
@login_required
def record(txn_type: str):
    if txn_type not in ("income", "expense"):
        abort(404)

    selected_day = _parse_day(request.args.get("date"))

    form = TransactionForm()
    categories = (
        Category.query
        .filter_by(type=txn_type, is_active=True)
        .order_by(Category.name)
        .all()
    )
    form.category.choices = [(c.id, c.name) for c in categories]

    if request.method == "GET":
        form.date.data = selected_day

    if not categories:
        flash("There are no active categories for this type yet. Ask an admin to add one.", "warning")

    if form.validate_on_submit():
        description = (form.description.data or "").strip() or None
        txn = Transaction(
            date=form.date.data,
            type=txn_type,
            category_id=form.category.data,
            amount_cents=form.amount_cents,
            payment_method=form.payment_method.data,
            description=description,
            recorded_by=current_user.id,
        )
        db.session.add(txn)
        db.session.flush()  # assign txn.id for the audit row
        record_audit(
            "create", user_id=current_user.id, entity="transaction", entity_id=txn.id,
            details={
                "type": txn_type,
                "amount_cents": txn.amount_cents,
                "category_id": txn.category_id,
                "date": txn.date.isoformat(),
            },
        )
        db.session.commit()
        flash(f"{txn_type.capitalize()} of {cents_to_str(txn.amount_cents)} saved.", "success")
        return redirect(url_for("main.index", date=form.date.data.isoformat()))

    return render_template(
        "main/record.html",
        form=form,
        txn_type=txn_type,
        selected_day=selected_day,
    )


@bp.route("/delete/<int:txn_id>", methods=["POST"])
@admin_required
def delete(txn_id: int):
    # CSRF check via the delete form.
    if not DeleteForm().validate_on_submit():
        abort(400)

    txn = db.session.get(Transaction, txn_id)
    if txn is None or txn.is_deleted:
        flash("That entry was not found.", "warning")
        return redirect(url_for("main.index"))

    # Soft delete only — the row stays for the audit trail.
    txn.is_deleted = True
    record_audit(
        "delete", user_id=current_user.id, entity="transaction", entity_id=txn.id,
        details={"type": txn.type, "amount_cents": txn.amount_cents, "date": txn.date.isoformat()},
    )
    db.session.commit()
    flash("Entry deleted.", "success")
    return redirect(url_for("main.index", date=txn.date.isoformat()))
