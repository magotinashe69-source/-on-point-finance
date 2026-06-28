# On Point Finance

A local-first, secure desktop web app for **On Point Educational Centre** to record
daily income and expenses and export branded PDF/Excel reports.

> See `SPEC.md` (full specification), `CLAUDE.md` (rules for Claude Code), and
> `BUILD_GUIDE.md` (the step-by-step build) — keep all three in this folder.

## This folder = Phase 1 (the secure skeleton)

No login or data yet — those come in Phases 2–4. What's wired: the application
factory, environment-based config, the database layer, login manager, CSRF
protection, rate limiter, and hardened session cookies.

## Run it

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your .env from the template
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

# 4. Put a strong secret key in .env. Generate one with:
python -c "import secrets; print(secrets.token_hex(32))"
#    paste the output after SECRET_KEY= in .env

# 5. Run
python run.py
```

Open <http://127.0.0.1:5000> — you should see "Phase 1 complete — the skeleton runs".

## Next

Open `BUILD_GUIDE.md` and start **Phase 2** (database models + your first admin user).
