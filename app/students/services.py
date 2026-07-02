"""Business logic for student records: search and CSV import.

Kept as plain functions (no request/response objects) so they are easy to test.
Routes stay thin and call into here.
"""

import csv
import io
from dataclasses import dataclass, field

from app.extensions import db
from app.models import Student

# The exact column headers the import expects (documented on the upload page and
# used to build the blank template).
CSV_HEADERS = ["full_name", "class_name", "guardian_name", "guardian_phone", "student_no"]


def _clean(value: str | None) -> str | None:
    """Trim whitespace; turn empty strings into None so optional fields stay NULL."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def search_students(query: str | None):
    """Active students, optionally filtered by a case-insensitive text query.

    The query matches on name, class, or guardian phone. All filtering goes
    through SQLAlchemy (parameterised) — never string-built SQL.
    """
    q = Student.query.filter(Student.is_active.is_(True))
    if query:
        term = query.strip()
        if term:
            like = f"%{term}%"
            q = q.filter(
                db.or_(
                    Student.full_name.ilike(like),
                    Student.class_name.ilike(like),
                    Student.guardian_phone.ilike(like),
                )
            )
    return q.order_by(Student.full_name).all()


@dataclass
class ImportSummary:
    """Counts for the post-import summary shown to the admin."""

    added: int = 0
    skipped_blank: int = 0
    skipped_no_name: int = 0
    skipped_duplicate: int = 0
    added_names: list[str] = field(default_factory=list)

    @property
    def skipped_total(self) -> int:
        return self.skipped_blank + self.skipped_no_name + self.skipped_duplicate

    def as_details(self) -> dict:
        """Compact dict for the AuditLog row (no personal data beyond counts)."""
        return {
            "added": self.added,
            "skipped_blank": self.skipped_blank,
            "skipped_no_name": self.skipped_no_name,
            "skipped_duplicate": self.skipped_duplicate,
        }


def _exists(full_name: str, class_name: str | None) -> bool:
    """True if an active-or-inactive student with the same name AND class exists."""
    return (
        Student.query.filter(
            Student.full_name == full_name,
            Student.class_name.is_(None) if class_name is None else Student.class_name == class_name,
        ).first()
        is not None
    )


def import_students_from_csv(raw_text: str) -> ImportSummary:
    """Parse CSV text and add new students to the session (caller commits).

    Rules (see Stage 1 brief):
      - skip completely blank rows,
      - require full_name (skip the row otherwise),
      - skip a row whose full_name AND class_name already exist (in the DB or
        earlier in this same file) so re-uploads don't duplicate.
    Returns an ImportSummary; does NOT commit — the route commits so the audit
    row and the inserts land together.
    """
    summary = ImportSummary()
    reader = csv.DictReader(io.StringIO(raw_text))

    # Track (name, class) pairs seen in this file to catch in-file duplicates too.
    seen: set[tuple[str, str | None]] = set()

    for row in reader:
        full_name = _clean(row.get("full_name"))
        class_name = _clean(row.get("class_name"))
        guardian_name = _clean(row.get("guardian_name"))
        guardian_phone = _clean(row.get("guardian_phone"))
        student_no = _clean(row.get("student_no"))

        # A row where every known column is empty is a blank row.
        if not any([full_name, class_name, guardian_name, guardian_phone, student_no]):
            summary.skipped_blank += 1
            continue

        if not full_name:
            summary.skipped_no_name += 1
            continue

        key = (full_name, class_name)
        if key in seen or _exists(full_name, class_name):
            summary.skipped_duplicate += 1
            continue
        seen.add(key)

        db.session.add(
            Student(
                full_name=full_name,
                class_name=class_name,
                guardian_name=guardian_name,
                guardian_phone=guardian_phone,
                student_no=student_no,
                is_active=True,
            )
        )
        summary.added += 1
        summary.added_names.append(full_name)

    return summary


def template_csv() -> str:
    """The blank template: just the header row, CRLF-terminated per RFC 4180."""
    buffer = io.StringIO()
    csv.writer(buffer).writerow(CSV_HEADERS)
    return buffer.getvalue()
