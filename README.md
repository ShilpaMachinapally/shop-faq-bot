# Shop FAQ Bot

A multi-shop FAQ application built with Flask, SQLAlchemy, Claude, and Resend.

## Features
- Free owner signup and login
- Each shop gets a unique public customer URL (`/s/<shop-slug>`)
- Shop-specific knowledge base, customer records, conversations, and pending questions
- Customer registration remembered in a two-day Flask session
- Claude answers using only the selected shop's knowledge and approved corrections
- Unknown questions become pending questions for the owner
- Owner answers are saved to that shop's knowledge base and emailed to the customer
- Owners can rate answers Good/Bad; Bad answers require a reason and corrected answer

## Local setup
1. Install Python 3.10+.
2. Create and activate a virtual environment.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your own values.
5. Run:
   `python app.py`
6. Open `http://127.0.0.1:5000`.

The default local database is SQLite. Set `DATABASE_URL` to your PostgreSQL connection string for deployment.

## Environment variables
- `SECRET_KEY`: random secret used to sign sessions.
- `DATABASE_URL`: SQLite or PostgreSQL database URL.
- `ANTHROPIC_API_KEY`: Claude API key. Without it, a conservative local knowledge matching fallback is used.
- `RESEND_API_KEY`: Resend API key.
- `RESEND_FROM_EMAIL`: verified sender identity for production email.
- `RESEND_TEST_MODE=true`: sends test messages to `delivered@resend.dev`; it does NOT send to the customer's email.
- `RESEND_TEST_MODE=false`: attempts delivery to the actual customer's email. Resend requires a verified sender/domain.

## Deployment notes
- Set the Render start command to `gunicorn app:app`.
- Set `SESSION_COOKIE_SECURE=true` when deployed behind HTTPS.
- Configure a persistent PostgreSQL database and environment variables in Render.
- `db.create_all()` is included for this small demo's first deployment. Use Flask-Migrate/Alembic for future schema changes.
- Never commit `.env`, API keys, database credentials, or the virtual environment.

## Customer links
New canonical link: `/s/<shop-slug>`.
The older `/shop/<shop-slug>` route redirects to the canonical link.
