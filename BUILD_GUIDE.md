# BUILD_GUIDE.md — Building On Point Finance in PyCharm with Claude Code

This walks you from an empty folder to a working, secure app. Work **one phase at a time**,
run it, then commit. Each phase has: what you're doing, the exact prompt to give Claude
Code, what to check, and the commit message.

Keep `SPEC.md` and `CLAUDE.md` in the project root the whole time — Claude Code reads
`CLAUDE.md` automatically every session, which is what keeps it consistent.

---

## Phase 0 — Set up your workshop (once)

You're preparing the tools before writing any app code.

1. **Install Python 3.11+** and **PyCharm** (Community is fine).
2. **Install Node.js** (Claude Code needs it), then install Claude Code:
   ```
   npm install -g @anthropic-ai/claude-code
   ```
3. Make the project folder and open it in PyCharm:
   ```
   mkdir on-point-finance
   cd on-point-finance
   git init
   ```
4. Create a **virtual environment** (an isolated Python just for this app, so its
   libraries don't clash with anything else):
   ```
   python -m venv .venv
   ```
   - Windows: `.venv\Scripts\activate`
   - Then in PyCharm: Settings → Project → Python Interpreter → select `.venv`.
5. Copy `SPEC.md` and `CLAUDE.md` into the folder.
6. Start Claude Code from the project folder:
   ```
   claude
   ```

**Why a venv?** It pins exact library versions to this project. Six months from now the app
still runs the same way. This is the habit that separates "works on my machine" from
"works."

✅ Check: `claude` opens and can see your files. `python --version` shows 3.11+.
📌 Commit: nothing yet — no code.

---

## Phase 1 — Project skeleton + security config

You're building the empty but secure shell: the app factory, config, and the safety
extensions wired in.

**Prompt to Claude Code:**
> Read CLAUDE.md and SPEC.md. Build Phase 1 only: the project skeleton.
> Create: requirements.txt (Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login,
> Flask-WTF, Flask-Limiter, python-dotenv, reportlab, openpyxl, pytest), a config.py with
> DevConfig/ProdConfig reading from environment, app/extensions.py defining db, migrate,
> login_manager, csrf and limiter, an app factory in app/__init__.py that registers them,
> a placeholder main blueprint with one "Hello, secure world" page behind @login_required,
> run.py, .env.example, and a .gitignore that excludes .env, .venv, instance/, __pycache__.
> Set secure session cookies (HttpOnly, SameSite=Lax) and a 30-minute session timeout.
> Then tell me how to install, run, and what I should see.

**Then you run:**
```
pip install -r requirements.txt
copy .env.example .env        # Windows (use cp on Mac/Linux)
```
Open `.env` and set a strong secret. Generate one with:
```
python -c "import secrets; print(secrets.token_hex(32))"
```
Paste it as `SECRET_KEY=...` in `.env`. **This key signs the login cookies — keep it secret,
never commit it.**

```
python run.py
```

✅ Check: visiting the page redirects you to a login (we build login next) or shows the
placeholder. No secret key appears in any committed file.
📌 Commit: `chore: secure project skeleton (factory, config, extensions)`

**What you learned:** the *app factory* pattern (build the app inside a function so tests
can build their own copy) and that all secrets come from `.env`, never code.

---

## Phase 2 — Database models + first admin user

You're creating the tables and a way to make the first login.

**Prompt:**
> Phase 2: database models from SPEC.md §4 — User, Category, Transaction, AuditLog —
> using SQLAlchemy. Money is amount_cents (integer). Transaction has is_deleted for soft
> delete. Add a money helper module app/money.py with cents_to_str and str_to_cents and a
> pytest test for both. Set up Flask-Migrate. Add two flask CLI commands: "seed-categories"
> (insert the SPEC seed categories) and "create-admin" (prompt for name/username/password,
> hash the password with Werkzeug, store the admin user). Show me the commands to run.

**Then you run:**
```
flask db init
flask db migrate -m "initial schema"
flask db upgrade
flask seed-categories
flask create-admin
```

✅ Check: `instance/finance.db` exists; `flask create-admin` makes a user; `pytest` passes
the money tests. Open the DB in PyCharm's database tool — confirm `password_hash` is a long
hash, **not** your plain password.
📌 Commit: `feat: data models, migrations, money helpers, admin CLI`

**What you learned:** *migrations* (versioned schema changes you can replay on any machine),
and why money lives as an integer — `str_to_cents("1500.00")` returns `150000`, no rounding
errors ever.

---

## Phase 3 — Authentication (the security core)

You're building login, logout, lockout, and rate limiting. Do this carefully — it guards
everything.

**Prompt:**
> Phase 3: authentication. Build an auth blueprint with login and logout using Flask-Login.
> Use a Flask-WTF LoginForm (CSRF protected). On login: look up the user; if locked_until is
> in the future, refuse with "Account locked, try again in 15 minutes"; on wrong password,
> increment failed_login_attempts and after 5 set locked_until = now + 15 minutes; on success,
> reset the counter and log them in. Rate-limit the login route with Flask-Limiter
> (e.g. 10 per minute). Write an AuditLog row on every login attempt (success/fail).
> Add @login_required everywhere and an admin_required decorator. Add a pytest test that 5
> bad logins locks the account. Friendly English errors only.

✅ Check: log in with your admin user; log out; deliberately fail 5 times and confirm the
lockout message; `pytest` passes the lockout test. Confirm the login form HTML contains a
hidden CSRF token.
📌 Commit: `feat: secure auth — login, lockout, rate limit, audit`

**What you learned:** passwords are never compared directly — Werkzeug hashes the input and
compares hashes. Lockout + rate limiting together make password-guessing impractical.

---

## Phase 4 — Record income & expenses + daily totals (the heart)

This is the screen your mom uses every day. Match the preview you already saw.

**Prompt:**
> Phase 4: the core recorder. In the main blueprint build: a dashboard at "/" with a date
> picker (default today) and three cards — Income today, Expenses today, Balance — computed
> from transactions on that date where is_deleted is False. Two big buttons open a CSRF-
> protected form (Flask-WTF) to record an entry: amount (MT, validated > 0, two decimals via
> str_to_cents), category (filtered by type), payment method, optional description, date.
> Below, list that day's entries with edit and delete (delete = soft delete + audit row;
> admin only). Totals update from the DB. English, big buttons, green income / red expense,
> navy/gold branding, display amounts with cents_to_str. Keep routes thin; put totals math in
> a testable function and test it.

✅ Check: record a few entries, see the cards change; pick yesterday's date and confirm it's
empty; delete one and confirm it disappears from the list but a row remains in the DB with
`is_deleted=1` plus an audit entry.
📌 Commit: `feat: daily income/expense recording with totals`

**What you learned:** keep calculations (the totals) in a plain function you can test, and
keep the route (the web plumbing) thin. That separation is what makes the app reliable.

---

## Phase 5 — Dashboard chart (offline)

You're adding a simple 7-day bar chart so trends are visible at a glance.

**Prompt:**
> Phase 5: add a last-7-days income-vs-expense bar chart to the dashboard using Chart.js.
> Download chart.umd.min.js into static/vendor/ and load it locally (must work offline — do
> not use a CDN). Provide the data from a thin route that returns daily totals for the last 7
> days. Keep the navy/gold colours.

✅ Check: turn the internet OFF, reload — the chart still renders.
📌 Commit: `feat: offline 7-day dashboard chart`

**What you learned:** for a local-first app, **bundle** your libraries. A CDN fails the day
the internet does — and that's the day she still needs to record fees.

---

## Phase 6 — Reports: PDF + Excel

You're building the **Download PDF** button (for real, server-side) and Excel export.

**Prompt:**
> Phase 6: reports blueprint. A reports page lets me pick a range (day / week / month /
> custom). "Download PDF" generates a branded PDF with ReportLab: navy header bar, gold
> accent, "On Point Educational Centre", "Quality Beyond Measure", the range, a table of
> entries (type, description, category, method, amount) and totals (income, expenses,
> balance). "Download Excel" exports the same rows with openpyxl. Add a monthly summary that
> groups income-by-category and expense-by-category with subtotals. Use cents_to_str for all
> displayed money. Filenames include the range.

✅ Check: download a day PDF and a month PDF; open in a viewer; numbers match the screen;
branding is correct; Excel opens in a spreadsheet.
📌 Commit: `feat: branded PDF + Excel reports with monthly summary`

**What you learned:** the browser preview used jsPDF; the real app generates PDFs in Python
(ReportLab) where you control branding precisely and can build week/month reports.

---

## Phase 7 — Roles, audit log view, settings

You're finishing the admin tools and locking down who can do what.

**Prompt:**
> Phase 7: admin blueprint (admin_required). Pages to: manage categories (add / activate /
> deactivate, never delete), manage users (add clerk/admin, deactivate, reset password),
> change my own password, and view the audit log (paginated, newest first). Clerks can record
> and view but cannot delete or reach admin pages. Enforce this on the server, not just by
> hiding buttons.

✅ Check: create a clerk user; log in as the clerk; confirm the admin pages return
"forbidden" even if you type the URL directly; confirm the clerk has no delete button.
📌 Commit: `feat: roles, user/category management, audit log view`

**What you learned:** security is enforced on the **server**. Hiding a button isn't security
— blocking the route is.

---

## Phase 8 — Backup

You're making it impossible to lose the history by accident.

**Prompt:**
> Phase 8: a "Back up now" admin action that creates a consistent copy of the SQLite database
> using "VACUUM INTO" to backups/finance-YYYYMMDD-HHMMSS.db, then confirms the path. Add a
> short note in the UI recommending the admin also turn on Windows BitLocker and copy the
> backups folder to Google Drive weekly.

✅ Check: click Back up now; confirm a timestamped file appears in `backups/` and opens as a
valid database.
📌 Commit: `feat: one-click database backup`

**What you learned:** `VACUUM INTO` makes a clean, complete copy even while the app is open —
safer than copying the live file.

---

## Phase 9 — Harden, test, and package as a desktop app

You're making it feel like a program she double-clicks, and protecting the money logic.

**Prompt:**
> Phase 9: (a) Add pytest tests covering money helpers, daily totals, login lockout, and
> soft-delete-keeps-the-row. (b) Add a ProdConfig and a run-prod path using waitress (a
> production WSGI server) instead of the debug server. (c) Create a start.bat that activates
> the venv, runs the app with waitress, and opens http://127.0.0.1:5000 in the default
> browser, so the admin just double-clicks one icon. Show me how to make a desktop shortcut.

✅ Check: `pytest` is all green; double-clicking `start.bat` opens the app in the browser;
debug mode is OFF in production.
📌 Commit: `chore: tests, production server, desktop launcher`

**What you learned:** the Flask debug server is for building, not daily use — `waitress` is a
small, sturdy server that's safe to leave running. The `.bat` turns the app into something
non-technical.

---

## How to run each day (for your mom)
1. Double-click the **On Point Finance** shortcut.
2. The browser opens to the login page.
3. Log in → record income/expenses → totals update.
4. Reports → Download PDF when the principal asks.
5. Once a week: Settings → Back up now, and copy the `backups` folder to Google Drive.

---

## Good habits while building
- **One phase, one commit.** If something breaks, you can step back one phase.
- **Read what Claude Code writes.** Ask it "explain this file line by line" on anything you
  don't follow — you're doing a CS degree; this is free tutoring on your own codebase.
- **Run after every phase.** Never stack two phases of unseen code.
- **If Claude Code drifts** (floats for money, raw SQL, skips CSRF), point it back to
  CLAUDE.md: "this violates rule 1/2/3 in CLAUDE.md, fix it." The rules file exists for
  exactly that moment.

---

## Quick reference — the security checklist
- [ ] SECRET_KEY in `.env`, never committed
- [ ] All routes `@login_required` (except login/static)
- [ ] Admin routes also `admin_required`, enforced server-side
- [ ] CSRF token on every form
- [ ] Passwords hashed (Werkzeug), never logged
- [ ] 5 fails → 15-min lockout, plus login rate limit
- [ ] All DB access via SQLAlchemy (no raw SQL)
- [ ] Money stored as integer centavos
- [ ] Transactions soft-deleted, audit row written
- [ ] Auto-logout after 30 min idle
- [ ] Backups working; BitLocker recommended
- [ ] Debug OFF in production (waitress)
