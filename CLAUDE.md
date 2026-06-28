# CLAUDE.md — Project rules for On Point Finance

Read this before writing any code. These rules are not optional.

## What this project is
A local-first, secure Flask + SQLite desktop web app for On Point Educational Centre to
record daily income and expenses and export branded PDF/Excel reports. Single office PC.
Must work fully offline. See SPEC.md for the full specification.

## Golden rules (most important first)

1. **Money is integer centavos.** Store `amount_cents: int` (1.500,00 MT → 150000).
   Never store money as float or in a Decimal column. Convert to/from a display string
   ONLY at the UI/report edge. Helper: `cents_to_str(150000) -> "1,500.00 MT"`,
   `str_to_cents("1500.00") -> 150000`. Put these in `app/money.py` and use them everywhere.

2. **No raw SQL, ever.** All database access goes through SQLAlchemy models / queries.
   This is our SQL-injection defence. No `db.session.execute("SELECT ... %s" % x)`.

3. **Every form is protected.** CSRF via Flask-WTF on all POST forms. Validate on the
   server side, not just the browser. Reject amount ≤ 0 and missing required fields.

4. **Every page needs auth.** Use `@login_required` on all routes except `auth.login`
   and static files. Admin-only routes also check `current_user.role == 'admin'`.

5. **Never hard-delete a transaction.** Set `is_deleted = True`. Filter `is_deleted == False`
   in all normal queries. Hard deletes destroy the audit trail.

6. **Log money actions.** On create / update / delete / restore / login, write an
   `AuditLog` row (user, action, entity, entity_id, JSON details, timestamp).

7. **Secrets live in `.env` only.** Never hardcode `SECRET_KEY`, never commit `.env` or
   `instance/finance.db`. Read config from environment via `config.py`.

## Conventions

- **Structure:** app factory in `app/__init__.py`; extensions (`db`, `migrate`,
  `login_manager`, `csrf`, `limiter`) in `app/extensions.py`; blueprints `auth`, `main`,
  `reports`, `admin`. Config classes in `config.py` (`DevConfig`, `ProdConfig`).
- **Migrations:** schema changes always via Flask-Migrate (`flask db migrate` +
  `flask db upgrade`). Never edit the DB by hand.
- **Branding:** navy `#16264d`, gold `#c9a227`. School name + "Quality Beyond Measure"
  on every report. English UI, plain words, big buttons, green = income, red = expense.
- **Payment methods:** Cash, M-Pesa, e-Mola, mKesh, Bank.
- **PDF = ReportLab. Excel = openpyxl. Charts = Chart.js bundled in `static/` (offline).**
- **Dates:** store `date` separately from `created_at`. Default new entries to today.
- **Errors to the user are friendly and English.** No stack traces shown to the admin.

## Coding style

- Small functions, clear names. Type hints on functions that touch money or auth.
- Put business logic in plain functions (testable) and keep routes thin.
- Write a pytest test whenever you add: a money helper, a total calculation, or an
  auth rule (e.g. lockout). Tests live in `tests/`.
- After finishing a phase, stop and tell me what to verify and what to commit.

## Things to never do

- Never invent a new money representation or skip validation "to move faster".
- Never disable CSRF or `@login_required` to make something work — fix the real cause.
- Never print or log passwords, hashes, or `.env` contents.
- Never add a dependency that needs system libraries (e.g. WeasyPrint/cairo) — keep it
  pip-only so it installs cleanly on Windows.

## How to work with me
Build one phase from SPEC.md §7 at a time. Explain what you're about to do in 2–3 lines,
write the code, then give me: (1) the command to run, (2) what I should see, (3) the
git commit message. Wait for me to confirm before the next phase.
