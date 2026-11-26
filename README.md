# Shop FAQ Bot

A multi-shop FAQ application built with Flask, SQLAlchemy, Google Gemini (gemini-3.8-flash), and Resend.

## Features
- Free owner signup and login
- Each shop gets a unique public customer URL (`/s/<shop-slug>`)
- Shop-specific knowledge base, customer records, conversations, and pending questions
- Customer registration with details and a two-day Flask session
- Google Gemini (gemini-3.8-flash) answers using only the selected shop's knowledge and owner-approved corrections- Unknown questions become pending questions for the owner
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
- `GEMINI_API_KEY`: Google Gemini API key.
- `GEMINI_MODEL`: Gemini model identifier. Defaults to `gemini-3.8-flash` if not configured.
- `EMAIL_PROVIDER`: `gmail` (default in `.env`) or `resend`. Selects how answer emails are sent.
- `GMAIL_ADDRESS`: Gmail address used to send when `EMAIL_PROVIDER=gmail`.
- `GMAIL_APP_PASSWORD`: Gmail app password (requires 2-Step Verification). Gmail SMTP attempts delivery to the customer's address.
- `EMAIL_FORCE_FAILURE=true`: forces every send attempt to fail for testing; the reason and attempt count are saved. Remove it or set it to `false` before real sending.
- `EMAIL_MAX_ATTEMPTS`: automatic send attempts per email before it is marked `Failed`. Defaults to `3` and is capped at `3`.
- `EMAIL_RETRY_BACKOFF_SECONDS`: base delay for exponential backoff between automatic retries. Defaults to `2`.
- `RESEND_API_KEY`: Resend API key (used when `EMAIL_PROVIDER=resend`).
- `RESEND_FROM_EMAIL`: verified sender identity for production email.
- `RESEND_TEST_MODE=true`: does NOT send to the customer; the email is recorded as `Failed` with the reason so it can be retried after test mode is disabled.
- `RESEND_TEST_MODE=false`: attempts delivery to the actual customer's email. Resend requires a verified sender/domain.

## Email delivery, failure saving, and retry
- Every owner-answer email is saved to the `email_deliveries` table BEFORE sending.
- Each send attempt is recorded (`attempts`, `status`, `last_error`, `provider_email_id`, `sent_at`).
- Failed sends are retried automatically with exponential backoff up to `EMAIL_MAX_ATTEMPTS` (maximum 3).
- If all automatic attempts fail, the email is marked `Failed` with the reason saved, and the owner can retry it manually from `/email-deliveries/<shop_id>`. Only failed emails show the Retry Email button; sent emails cannot be retried.
- `Sent` means only that the email provider accepted the message. It does not confirm that the message reached the customer's inbox; use real inbox verification when that proof is required.
- Run `python test_email_delivery.py` for isolated send, failure-saving, and retry checks.
- Run `python demo_email_delivery.py` to send a real answer email to a real inbox and verify receipt via IMAP (uses an isolated SQLite database, not production).

## Deployment notes
- Set the Render start command to `gunicorn app:app`.
- Set `SESSION_COOKIE_SECURE=true` when deployed behind HTTPS.
- Configure a persistent PostgreSQL database and environment variables in Render.
- `db.create_all()` is included for this small demo's first deployment. Use Flask-Migrate/Alembic for future schema changes.
- Never commit `.env`, API keys, database credentials, or the virtual environment.

## Customer links
New canonical link: `/s/<shop-slug>`. Customers sign in or register there before the chatbot opens.
The older `/shop/<shop-slug>` route redirects to the canonical link.
