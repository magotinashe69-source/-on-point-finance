"""SQLAlchemy models for On Point Finance (see SPEC.md section 4).

Money lives in Transaction.amount_cents as an Integer of centavos — never a
float or Decimal column. Transactions are soft-deleted (is_deleted), never
hard-deleted, so the audit trail stays intact.
"""

from datetime import date, datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp for created_at / updated_at defaults."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="clerk")  # admin | clerk
    # NOTE: this column intentionally overrides Flask-Login's UserMixin.is_active
    # property, so a disabled user is also treated as not-active for login.
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    def set_password(self, password: str) -> None:
        """Hash and store a password (Werkzeug pbkdf2/scrypt + per-user salt)."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if the password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # income | expense
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.UniqueConstraint("name", "type", name="uq_category_name_type"),
    )

    def __repr__(self) -> str:
        return f"<Category {self.name} ({self.type})>"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)  # day money moved
    type = db.Column(db.String(20), nullable=False)  # income | expense
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)  # integer centavos, never float
    payment_method = db.Column(db.String(20), nullable=False)  # Cash, M-Pesa, e-Mola, mKesh, Bank
    receipt_no = db.Column(db.String(60), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False, index=True)  # soft delete
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    category = db.relationship("Category")
    recorder = db.relationship("User")

    def __repr__(self) -> str:
        return f"<Transaction {self.type} {self.amount_cents}c on {self.date}>"


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(40), nullable=False)  # login / create / update / delete / restore
    entity = db.Column(db.String(40), nullable=True)  # e.g. "transaction"
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON of old/new values
    timestamp = db.Column(db.DateTime, nullable=False, default=_utcnow)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity}:{self.entity_id}>"


@login_manager.user_loader
def load_user(user_id: str):
    """Tell Flask-Login how to load a user from the session id."""
    return db.session.get(User, int(user_id))
