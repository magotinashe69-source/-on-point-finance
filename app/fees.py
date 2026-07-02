"""Fee logic: the single source of truth linking a student's grade to a tuition.

Everything about "which fee costs how much" lives here so it is easy to change:
  - the class_name -> grade_band mapping (grade_band_for_class),
  - looking up the amount for a student + fee type (fee_amount_cents),
  - the default amounts inserted by `flask seed-fees` (seed_fees).

Amounts are integer centavos, as everywhere else in the app.
"""

import re
from typing import Optional

from app.extensions import db
from app.models import GradeFee, Category, Student

# --- Fee types shown in the record-income dropdown -------------------------
FEE_TUITION = "Tuition"
FEE_REGISTRATION = "Registration"
FEE_FOOD = "Food"
FEE_TYPES = [FEE_TUITION, FEE_REGISTRATION, FEE_FOOD]

# --- Grade bands (also the GradeFee.grade_band keys for tuition) -----------
BAND_ECD = "ECDA-B"
BAND_1_2 = "Grade 1-2"
BAND_3_7 = "Grade 3-7"

# Default seed amounts, in integer centavos. Fees are whole meticais, so these
# are the metical value x 100 (e.g. 4,500 MT -> 450000). The school can adjust
# them later from the database; they are the starting point only.
DEFAULT_FEES_CENTS = {
    BAND_ECD: 350000,     # 3,500 MT
    BAND_1_2: 400000,     # 4,000 MT
    BAND_3_7: 450000,     # 4,500 MT
    FEE_REGISTRATION: 300000,  # 3,000 MT
    FEE_FOOD: 120000,          # 1,200 MT
}

# Which income Category a fee maps to when the payment is saved.
FEE_CATEGORY_NAME = {
    FEE_TUITION: "Tuition",
    FEE_REGISTRATION: "Registration",
    FEE_FOOD: "Food",
}


def grade_band_for_class(class_name: Optional[str]) -> Optional[str]:
    """Map a student's stored class_name to a grade band, or None if unmatched.

    THE ONE PLACE this mapping lives — change the rules here only.
      - "ECD", "ECDA", "ECD B", "Pre-primary"  -> ECDA-B
      - a grade number 1-2                       -> Grade 1-2
      - a grade number 3-7                       -> Grade 3-7
      - anything else (Grade 8+, blank, "Staff") -> None
    """
    if not class_name:
        return None
    text = " ".join(class_name.strip().lower().split())
    if not text:
        return None

    # Early childhood classes.
    if text.startswith("ecd") or text.startswith("pre"):
        return BAND_ECD

    # Numbered grades: pull the first number out of "grade 5", "gr 1", "5".
    match = re.search(r"\d+", text)
    if match:
        n = int(match.group())
        if 1 <= n <= 2:
            return BAND_1_2
        if 3 <= n <= 7:
            return BAND_3_7

    return None


def _amount_for_band(grade_band: str) -> Optional[int]:
    """Active GradeFee amount (centavos) for a band key, or None if not set."""
    fee = GradeFee.query.filter_by(grade_band=grade_band, is_active=True).first()
    return fee.tuition_cents if fee else None


def tuition_cents_for_student(student: Student) -> Optional[int]:
    """Tuition (centavos) derived from the student's stored grade, or None.

    Returns None when the class_name matches no band, OR when the matched band
    has no active GradeFee row yet. The caller fills 0 and flags "grade not
    matched" so the amount can still be typed by hand.
    """
    band = grade_band_for_class(student.class_name)
    if band is None:
        return None
    return _amount_for_band(band)


def fee_amount_cents(student: Student, fee_type: str) -> Optional[int]:
    """Amount (centavos) for a student + fee type. Tuition is grade-derived;
    Registration/Food are flat. Returns None if it cannot be determined."""
    if fee_type == FEE_TUITION:
        return tuition_cents_for_student(student)
    return _amount_for_band(fee_type)


def income_category_for_fee(fee_type: str) -> Category:
    """The income Category a fee maps to, creating it (active) if missing.

    Keeps the saved transaction on a sensible category without forcing the admin
    to pre-create one. Caller commits.
    """
    name = FEE_CATEGORY_NAME.get(fee_type, fee_type)
    category = Category.query.filter_by(name=name, type="income").first()
    if category is None:
        category = Category(name=name, type="income", is_active=True)
        db.session.add(category)
        db.session.flush()  # assign category.id for the transaction
    return category


def seed_fees() -> int:
    """Upsert the default GradeFee rows. Returns how many were created or corrected.

    Inserts any missing rows AND repairs the amount of any existing row that does
    not match the correct value — so re-running fixes wrong data already stored
    (e.g. the earlier 100x-too-small fees). Idempotent: a second run with correct
    data returns 0. Used by `flask seed-fees` and tests. Commits itself.
    """
    changed = 0
    for band, cents in DEFAULT_FEES_CENTS.items():
        fee = GradeFee.query.filter_by(grade_band=band).first()
        if fee is None:
            db.session.add(GradeFee(grade_band=band, tuition_cents=cents, is_active=True))
            changed += 1
        elif fee.tuition_cents != cents:
            fee.tuition_cents = cents  # repair a wrong (e.g. 100x-too-small) value
            changed += 1
    db.session.commit()
    return changed
