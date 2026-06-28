# On Point Finance — Specification (SPEC.md)

A local-first, secure desktop web app for **On Point Educational Centre** to record
daily income and expenses, see totals, and export branded PDF/Excel reports.

> Motto on every report: *Quality Beyond Measure*
> Primary user: the school administrator (new to PCs). Design for clarity and safety.

---

## 1. Goals and non-goals

**Goals**
- Record each day's income and expenses in seconds, with no jargon.
- Always show today's totals: income, expenses, balance.
- Export a clean, branded PDF (and Excel) of any day, week, or month.
- Keep the financial history safe: backups, audit trail, no silent data loss.
- Work fully **offline** — internet in Tete is not guaranteed.

**Non-goals (for v1)**
- Multi-device / cloud sync (possible later via Render + PostgreSQL).
- Full accounting (ledgers, double-entry, tax). This is a cashbook, not Sage.
- Payroll. Salaries are recorded as expenses, not calculated.

---

## 2. Technology stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Your stack; CS coursework |
| Web framework | Flask (app-factory + blueprints) | You know it; full UI control |
| Database | SQLite (single file) | No server, trivial backup, offline |
| ORM | SQLAlchemy + Flask-Migrate | Parameterised queries (no SQL injection), safe schema changes |
| Auth | Flask-Login + Werkzeug hashing | Sessions + salted password hashes |
| Forms / CSRF | Flask-WTF | Server-side validation + CSRF protection |
| Brute-force defence | Flask-Limiter + DB lockout | Stops password guessing |
| PDF | ReportLab | Pure Python, no system libraries, works on Windows |
| Excel | openpyxl | Simple .xlsx export |
| Charts | Chart.js (bundled locally) | Dashboard graphs, offline |
| Config / secrets | python-dotenv (.env) | Keep keys out of code and git |
| Tests | pytest | Protect money logic from regressions |

**Money rule (non-negotiable):** money is stored as an **integer of centavos**
(`amount_cents`). 1.500,00 MT = `150000`. Never use float/Decimal columns for storage.
Format for display only, at the edge.

---

## 3. Security model

**Threat model (be honest about what we defend against):**
This runs on one office PC. The real risks are: a lost/stolen laptop, someone walking
up to an unattended PC, accidental deletion, and disk failure. We defend against those.

**Controls**
1. **Login required** for every page except the login screen.
2. **Password hashing** with Werkzeug (`pbkdf2:sha256` or `scrypt`) + per-user salt. Plain
   passwords are never stored or logged.
3. **Account lockout**: after 5 failed logins, lock the account for 15 minutes
   (`failed_login_attempts`, `locked_until` on the user row).
4. **Rate limiting** on the login route (Flask-Limiter) as a second layer.
5. **CSRF protection** on every form (Flask-WTF).
6. **No raw SQL** — all DB access via SQLAlchemy (parameterised), preventing SQL injection.
7. **Secure session cookies**: `HttpOnly`, `SameSite=Lax`, and an **auto-logout** after
   30 minutes of inactivity (`PERMANENT_SESSION_LIFETIME`).
8. **Roles**: `admin` (full access, manage users/categories, delete) vs `clerk`
   (add and view only).
9. **Soft delete** for transactions (`is_deleted=True`), never a hard `DELETE` — money
   records must remain auditable.
10. **Audit log**: every create / edit / delete / login records who, what, when.
11. **Secrets in `.env`** only; `.env` and the database are git-ignored.
12. **Backups**: one-click timestamped copy of the DB (uses SQLite `VACUUM INTO` for a
    clean, consistent file). Recommend pairing with **Windows BitLocker** for disk
    encryption — the strongest single protection for a stolen laptop.

**Out of scope for v1 (documented, not hidden):** encryption-at-rest inside the app
(rely on OS disk encryption), network/TLS hardening (app is localhost-only).

---

## 4. Data model

### users
| field | type | notes |
|---|---|---|
| id | int PK | |
| name | str | display name |
| username | str unique | login |
| password_hash | str | Werkzeug hash |
| role | str | `admin` or `clerk` |
| is_active | bool | disable instead of delete |
| failed_login_attempts | int | for lockout |
| locked_until | datetime null | lockout expiry |
| created_at | datetime | |

### categories
| field | type | notes |
|---|---|---|
| id | int PK | |
| name | str | e.g. Tuition, Salaries |
| type | str | `income` or `expense` |
| is_active | bool | hide without deleting |

Seed income: Tuition, Registration, Exam fees, Uniforms, Transport, Donations.
Seed expense: Salaries, Rent, Electricity, Internet, Materials, Maintenance, Cleaning, Cambridge fees.

### transactions
| field | type | notes |
|---|---|---|
| id | int PK | |
| date | date | the day the money moved (≠ created_at) |
| type | str | `income` or `expense` |
| category_id | int FK | → categories |
| amount_cents | int | **integer centavos, never float** |
| payment_method | str | Cash, M-Pesa, e-Mola, mKesh, Bank |
| receipt_no | str null | paper-trail reference |
| description | str null | free text |
| recorded_by | int FK | → users |
| is_deleted | bool | soft delete |
| created_at | datetime | |
| updated_at | datetime | |

### audit_log
| field | type | notes |
|---|---|---|
| id | int PK | |
| user_id | int FK | who |
| action | str | login / create / update / delete / restore |
| entity | str | e.g. transaction |
| entity_id | int null | which row |
| details | text | JSON of old/new values |
| timestamp | datetime | |

---

## 5. Screens

1. **Login** — username, password. Friendly error: "Wrong username or password."
   After 5 fails: "Account locked. Try again in 15 minutes."
2. **Dashboard** — date picker (default today); cards for Income / Expenses / Balance;
   a small bar chart of the last 7 days; quick "Record Income" / "Record Expense".
3. **Record entry** — amount (MT), category (dropdown), payment method, description,
   date. Hard validation: amount > 0, two decimals, required fields.
4. **Day view / entries** — list for the selected day with edit and delete (admin),
   plus running totals. Filters by type/category/method.
5. **Reports** — choose a range (day / week / month / custom) → on-screen summary +
   **Download PDF** + **Download Excel**.
6. **Settings (admin only)** — manage categories, manage users, change password,
   **Back up now**, view audit log.

UI: English, plain words, big buttons, green = income, red = expense.
Currency display: `1,500.00 MT`. (If Portuguese is wanted later, it's a label swap.)

---

## 6. Reports

- **PDF (ReportLab):** navy header bar, gold accent, school name + "Quality Beyond Measure",
  date/range, a table of entries (type, description, category, method, amount),
  then totals (income, expenses, balance). Filename: `on-point-record-<range>.pdf`.
- **Excel (openpyxl):** same columns as a real sheet she can sort/total herself.
- A **monthly summary** groups income-by-category and expense-by-category with subtotals.

---

## 7. Build phases (ship one at a time, commit after each)

1. Skeleton: app factory, config, extensions, `.env`, `.gitignore`, run.py.
2. Models + first migration + seed categories + create first admin user (CLI command).
3. Auth: login/logout, hashing, `@login_required`, lockout, rate limit, auto-logout.
4. Core: record income/expense, day view, totals (CSRF + validation everywhere).
5. Dashboard: summary cards + 7-day chart (Chart.js bundled).
6. Reports: PDF + Excel + monthly summary.
7. Audit log + soft delete + roles.
8. Backup (VACUUM INTO) + Settings (users, categories, change password).
9. Hardening: tests for money math + auth; package as a desktop launcher.

Definition of done for each phase: it runs, the happy path works, and you committed it.

---

## 8. Acceptance checks (v1 is "done" when…)

- [ ] Cannot reach any page without logging in.
- [ ] 5 wrong passwords locks the account for 15 minutes.
- [ ] Recording 1500.00 stores `150000` and displays `1,500.00 MT`.
- [ ] Deleting an entry hides it but keeps it in the DB + writes an audit row.
- [ ] PDF and Excel download for a chosen day and month, branded correctly.
- [ ] "Back up now" produces a timestamped copy that opens correctly.
- [ ] App works with the internet switched off.
- [ ] `pytest` passes for money formatting and login lockout.
