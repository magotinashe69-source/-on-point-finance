"""Account-lockout logic, kept as plain testable functions (no Flask here).

Times use NAIVE UTC because that is what SQLite returns for a DateTime column;
mixing naive and timezone-aware datetimes would raise at comparison time.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models import User

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def naive_utcnow() -> datetime:
    """Current UTC time as a naive datetime (matches values read from SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_locked(user: User, now: Optional[datetime] = None) -> bool:
    """True if the account is currently locked."""
    now = now or naive_utcnow()
    return user.locked_until is not None and user.locked_until > now


def register_failed_login(user: User, now: Optional[datetime] = None) -> None:
    """Count a failed attempt; lock for LOCKOUT_MINUTES once the limit is hit."""
    now = now or naive_utcnow()
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)


def register_successful_login(user: User) -> None:
    """Clear the failure counter and any lock after a good login."""
    user.failed_login_attempts = 0
    user.locked_until = None
