#!/usr/bin/env python
"""Read-only health check for the On Point Finance database.

Confirms the app is actually using PostgreSQL (Neon), can connect, has the
expected tables and data, and is at the latest migration.

READ-ONLY: this script only runs SELECTs and reads metadata. It never inserts,
updates, deletes, drops, or alters anything.

Run any time from anywhere:
    python scripts/check_db.py
"""

import os
import sys

# Make the project importable and load its .env, no matter where we run from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from sqlalchemy import inspect, text, func  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from alembic.runtime.migration import MigrationContext  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User, Category, Transaction  # noqa: E402

REQUIRED_TABLES = ["users", "categories", "transactions", "audit_log"]

results = []  # list of (label, passed: bool)


def report(label: str, passed: bool, detail: str) -> None:
    results.append((label, passed))
    print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    print(f"        {detail}")


def main() -> int:
    app = create_app()
    with app.app_context():
        # 1. Which database is the app actually using? (scheme only — no secrets)
        uri = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
        scheme = uri.split("://", 1)[0] if "://" in uri else "(none)"
        is_postgres = scheme.startswith("postgresql")
        report(
            "1. Database in use",
            is_postgres,
            f"scheme = '{scheme}://'  ->  "
            + ("PostgreSQL" if is_postgres else "NOT PostgreSQL (expected postgresql://)"),
        )

        # 2. Real connection + SELECT version()
        try:
            with db.engine.connect() as conn:
                version = conn.execute(text("SELECT version();")).scalar()
            report("2. Connectivity (SELECT version())", True, str(version))
        except Exception as exc:  # noqa: BLE001 - report any failure
            report("2. Connectivity (SELECT version())", False, f"{type(exc).__name__}: {exc}")

        # 3. Required tables present
        try:
            tables = set(inspect(db.engine).get_table_names())
            missing = [t for t in REQUIRED_TABLES if t not in tables]
            report(
                "3. Required tables present",
                not missing,
                "found all: " + ", ".join(REQUIRED_TABLES)
                if not missing
                else f"MISSING: {', '.join(missing)} (present: {', '.join(sorted(tables)) or 'none'})",
            )
        except Exception as exc:  # noqa: BLE001
            report("3. Required tables present", False, f"{type(exc).__name__}: {exc}")

        # 4. Row counts (read-only, via ORM). Informational checks.
        try:
            counts = {
                "categories": db.session.query(func.count()).select_from(Category).scalar(),
                "users": db.session.query(func.count()).select_from(User).scalar(),
                "transactions": db.session.query(func.count()).select_from(Transaction).scalar(),
            }
            notes = []
            if counts["categories"] <= 0:
                notes.append("categories=0 -> run `flask seed-categories`")
            if counts["users"] < 1:
                notes.append("users=0 -> run `flask create-admin`")
            detail = (
                f"categories={counts['categories']}, users={counts['users']}, "
                f"transactions={counts['transactions']}"
            )
            if notes:
                detail += "  | NOTE: " + "; ".join(notes)
            # PASS if counts are readable AND the expected baseline holds
            # (categories seeded and at least one user).
            ok = counts["categories"] > 0 and counts["users"] >= 1
            report("4. Row counts", ok, detail)
        except Exception as exc:  # noqa: BLE001
            report("4. Row counts", False, f"{type(exc).__name__}: {exc}")

        # 5. No pending migrations (db revision == latest script head)
        try:
            cfg = AlembicConfig()
            cfg.set_main_option("script_location", os.path.join(PROJECT_ROOT, "migrations"))
            head = ScriptDirectory.from_config(cfg).get_current_head()
            with db.engine.connect() as conn:
                db_rev = MigrationContext.configure(conn).get_current_revision()
            up_to_date = head is not None and db_rev == head
            report(
                "5. Migrations up to date",
                up_to_date,
                f"db revision = {db_rev}, latest = {head}"
                + ("" if up_to_date else "  -> pending! run `flask db upgrade`"),
            )
        except Exception as exc:  # noqa: BLE001
            report("5. Migrations up to date", False, f"{type(exc).__name__}: {exc}")

    # --- Summary ---
    print("\n" + "=" * 64)
    overall = all(passed for _, passed in results)
    if overall:
        print("OVERALL: PASS - app is on PostgreSQL, reachable, schema present, "
              "seeded, and at the latest migration.")
        return 0

    first_fail = next(label for label, passed in results if not passed)
    fixes = {
        "1. Database in use": "DATABASE_URL is not set/loaded -> add it to .env so the "
                              "app uses Neon instead of the local SQLite fallback.",
        "2. Connectivity (SELECT version())": "Cannot reach the database -> check the Neon "
                              "connection string, network, and that the password is current.",
        "3. Required tables present": "Schema not created on this database -> run "
                              "`flask db upgrade`.",
        "4. Row counts": "Database is empty -> run `flask seed-categories` and "
                              "`flask create-admin`.",
        "5. Migrations up to date": "Pending migrations -> run `flask db upgrade`.",
    }
    print(f"OVERALL: FAIL - first failing check: {first_fail}")
    print(f"Most likely cause/fix: {fixes.get(first_fail, 'see the detail above.')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
