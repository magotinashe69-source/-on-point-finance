"""Stage 2 tests: grade->tuition corroboration and smart income recording."""

from datetime import date

from app.extensions import db
from app.models import Student, Transaction, GradeFee
from app.fees import (
    seed_fees,
    grade_band_for_class,
    tuition_cents_for_student,
    BAND_ECD, BAND_1_2, BAND_3_7,
)

GOOD_PASSWORD = "correct-horse-8"


def _login(client, username, password):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)


def _student(full_name, class_name):
    s = Student(full_name=full_name, class_name=class_name, is_active=True)
    db.session.add(s)
    db.session.commit()
    return s


# --- Grade-band mapping is the single source of truth ----------------------

def test_band_mapping_buckets_grades():
    assert grade_band_for_class("Grade 1") == BAND_1_2
    assert grade_band_for_class("Grade 2") == BAND_1_2
    assert grade_band_for_class("Grade 5") == BAND_3_7
    assert grade_band_for_class("ECD A") == BAND_ECD
    assert grade_band_for_class("Pre-primary") == BAND_ECD
    # Unmatched: too high, blank, or non-grade text.
    assert grade_band_for_class("Grade 9") is None
    assert grade_band_for_class("") is None
    assert grade_band_for_class(None) is None
    assert grade_band_for_class("Staff") is None


def test_tuition_derived_from_stored_grade(app):
    seed_fees()
    grade1 = _student("Ana One", "Grade 1")
    grade5 = _student("Bem Five", "Grade 5")
    ecd = _student("Cita ECD", "ECD B")

    assert tuition_cents_for_student(grade1) == 4000   # Grade 1-2
    assert tuition_cents_for_student(grade5) == 4500   # Grade 3-7
    assert tuition_cents_for_student(ecd) == 3500      # ECDA-B


def test_unmatched_grade_returns_none(app):
    seed_fees()
    nomatch = _student("Dino Nine", "Grade 9")
    assert tuition_cents_for_student(nomatch) is None
    # Also None when the band matches but no fee is seeded.
    db.session.query(GradeFee).delete()
    db.session.commit()
    assert tuition_cents_for_student(_student("Eva One", "Grade 1")) is None


def test_seed_fees_is_idempotent(app):
    assert seed_fees() == 5      # ECDA-B, 1-2, 3-7, Registration, Food
    assert seed_fees() == 0      # nothing added the second time
    assert GradeFee.query.count() == 5


# --- Saving a smart income payment -----------------------------------------

def test_saved_fee_payment_has_student_and_amount(client, user):
    seed_fees()
    _login(client, "admin", GOOD_PASSWORD)
    student = _student("Ana One", "Grade 1")

    resp = client.post("/record/fee", data={
        "student": student.id,
        "fee_type": "Tuition",
        "amount": "40.00",           # 4000 cents
        "payment_method": "Cash",
        "date": date.today().isoformat(),
        "description": "Tuition - Ana One (Grade 1)",
    }, follow_redirects=True)
    assert resp.status_code == 200

    txn = Transaction.query.filter_by(student_id=student.id).one()
    assert txn.amount_cents == 4000
    assert txn.type == "income"
    assert txn.category.name == "Tuition"
    assert txn.category.type == "income"


def test_manual_income_still_has_no_student(client, user):
    # Stage 1 manual recording keeps working: student_id stays NULL.
    from app.models import Category
    _login(client, "admin", GOOD_PASSWORD)
    cat = Category(name="Donations", type="income", is_active=True)
    db.session.add(cat)
    db.session.commit()

    client.post("/record/income", data={
        "amount": "100.00",
        "category": cat.id,
        "payment_method": "Cash",
        "date": date.today().isoformat(),
    }, follow_redirects=True)

    txn = Transaction.query.filter_by(category_id=cat.id).one()
    assert txn.student_id is None
    assert txn.amount_cents == 10000
