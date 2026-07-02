"""Routes for the students blueprint. Every route requires login.

Adding and searching are open to any logged-in user; deactivating and CSV import
are admin-only (server-enforced with @admin_required).
"""

from flask import render_template, request, redirect, url_for, flash, abort, Response
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Student
from app.audit import record_audit
from app.auth.decorators import admin_required
from app.students import bp
from app.students.forms import AddStudentForm, ImportForm, ActionForm
from app.students.services import (
    search_students,
    import_students_from_csv,
    template_csv,
)


def _clean(value):
    """Trim a form field; empty -> None so optional columns stay NULL."""
    value = (value or "").strip()
    return value or None


@bp.route("/")
@login_required
def index():
    query = request.args.get("q", "").strip()
    students = search_students(query)
    return render_template(
        "students/list.html",
        students=students,
        query=query,
        action=ActionForm(),
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    form = AddStudentForm()
    if form.validate_on_submit():
        student = Student(
            full_name=form.full_name.data.strip(),
            class_name=_clean(form.class_name.data),
            guardian_name=_clean(form.guardian_name.data),
            guardian_phone=_clean(form.guardian_phone.data),
            student_no=_clean(form.student_no.data),
            is_active=True,
        )
        db.session.add(student)
        db.session.flush()  # assign student.id for the audit row
        record_audit(
            "create_student", user_id=current_user.id, entity="student", entity_id=student.id,
            details={"full_name": student.full_name, "class_name": student.class_name},
        )
        db.session.commit()
        flash(f"Student '{student.full_name}' was added.", "success")
        return redirect(url_for("students.index"))

    return render_template("students/add.html", form=form)


@bp.route("/<int:student_id>/deactivate", methods=["POST"])
@admin_required
def deactivate(student_id: int):
    # CSRF check via the action form.
    if not ActionForm().validate_on_submit():
        abort(400)

    student = db.session.get(Student, student_id)
    if student is None or not student.is_active:
        flash("That student was not found.", "warning")
        return redirect(url_for("students.index"))

    student.is_active = False  # never hard delete — keep the record
    record_audit(
        "deactivate_student", user_id=current_user.id, entity="student", entity_id=student.id,
        details={"full_name": student.full_name, "class_name": student.class_name},
    )
    db.session.commit()
    flash(f"Student '{student.full_name}' was deactivated.", "success")
    return redirect(url_for("students.index"))


@bp.route("/import", methods=["GET", "POST"])
@admin_required
def import_csv():
    form = ImportForm()
    summary = None

    if form.validate_on_submit():
        raw = form.file.data.read()
        # CSV files may arrive as UTF-8 (often with a BOM from Excel). Decode
        # forgivingly so a stray byte never shows a stack trace to the admin.
        text = raw.decode("utf-8-sig", errors="replace")

        summary = import_students_from_csv(text)
        record_audit(
            "import_students", user_id=current_user.id, entity="student",
            details=summary.as_details(),
        )
        db.session.commit()
        flash(
            f"Import finished: {summary.added} added, {summary.skipped_total} skipped.",
            "success",
        )

    return render_template("students/import.html", form=form, summary=summary)


@bp.route("/import/template.csv")
@admin_required
def import_template():
    """Download a blank CSV with just the expected header row."""
    return Response(
        template_csv(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=students_template.csv"},
    )
