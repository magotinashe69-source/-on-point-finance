"""Audit logging helper.

One place to write an AuditLog row so every money/auth action is recorded the
same way. Never put passwords or hashes in `details` (CLAUDE.md rule).
"""

import json
from typing import Any, Optional

from app.extensions import db
from app.models import AuditLog


def record_audit(
    action: str,
    *,
    user_id: Optional[int] = None,
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """Add an AuditLog row to the session (caller commits).

    `details` is stored as JSON text. The timestamp is set by the model default.
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=json.dumps(details) if details is not None else None,
    )
    db.session.add(log)
    return log
