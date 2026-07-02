"""Routes for the main blueprint: dashboard, record entry, soft delete."""

from datetime import date, datetime

from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Category, Transaction, Student
from app.money import cents_to_str
from app.audit import record_audit
from app.auth.decorators import admin_required
from app.fees import (
    FEE_TYPES,
    grade_band_for_class,
    tuition_cents_for_student,
    fee_amount_cents,
    income_category_for_fee,
)
from app.main import bp
from app.main.forms import TransactionForm, StudentIncomeForm, DeleteForm
from app.main.services import compute_totals, transactions_on, last_7_days_series


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


@bp.route("/api/last-7-days")
@login_required
def chart_data():
    """JSON for the dashboard chart: 7 days ending on the selected date."""
    end_day = _parse_day(request.args.get("date"))
    return jsonify(last_7_days_series(end_day))


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


@bp.route("/record/fee", methods=["GET", "POST"])
@login_required
def record_student_income():
    """Smart income: record a fee payment against a stored student.

    The grade comes from the student's stored record (never re-typed) and the
    tuition amount is derived from that grade via the GradeFee table, so the
    saved money always corroborates the database.
    """
    selected_day = _parse_day(request.args.get("date"))

    students = (
        Student.query.filter(Student.is_active.is_(True))
        .order_by(Student.full_name)
        .all()
    )

    form = StudentIncomeForm()
    # Option text shows name AND grade so the user can confirm the right child.
    form.student.choices = [
        (s.id, f"{s.full_name} — {s.class_name or 'grade not set'}") for s in students
    ]
    form.fee_type.choices = [(f, f) for f in FEE_TYPES]

    if request.method == "GET":
        form.date.data = selected_day

    if not students:
        flash("There are no active students yet. Add a student first.", "warning")

    if form.validate_on_submit():
        student = db.session.get(Student, form.student.data)
        if student is None or not student.is_active:
            flash("Please choose a valid student.", "error")
        else:
            category = income_category_for_fee(form.fee_type.data)
            description = (form.description.data or "").strip() or None
            txn = Transaction(
                date=form.date.data,
                type="income",
                category_id=category.id,
                amount_cents=form.amount_cents,
                payment_method=form.payment_method.data,
                description=description,
                recorded_by=current_user.id,
                student_id=student.id,
            )
            db.session.add(txn)
            db.session.flush()  # assign txn.id for the audit row
            record_audit(
                "create", user_id=current_user.id, entity="transaction", entity_id=txn.id,
                details={
                    "type": "income",
                    "amount_cents": txn.amount_cents,
                    "category_id": txn.category_id,
                    "student_id": student.id,
                    "fee_type": form.fee_type.data,
                    "date": txn.date.isoformat(),
                },
            )
            db.session.commit()
            flash(
                f"Income of {cents_to_str(txn.amount_cents)} for {student.full_name} saved.",
                "success",
            )
            return redirect(url_for("main.index", date=form.date.data.isoformat()))

    # Data for the client-side (offline) auto-fill: per-student grade + tuition,
    # plus the flat fee amounts. Amounts are integer centavos; JS divides by 100.
    student_data = {
        str(s.id): {
            "name": s.full_name,
            "grade": s.class_name or "",
            "band": grade_band_for_class(s.class_name),
            "tuition_cents": tuition_cents_for_student(s),
        }
        for s in students
    }
    fee_amounts = {
        "Tuition": None,  # per-student, taken from student_data
        "Registration": fee_amount_cents(None, "Registration"),
        "Food": fee_amount_cents(None, "Food"),
    }

    return render_template(
        "main/record_fee.html",
        form=form,
        selected_day=selected_day,
        student_data=student_data,
        fee_amounts=fee_amounts,
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
