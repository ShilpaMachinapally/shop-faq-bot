"""End-to-end proof that a customer answer email lands in a REAL inbox.

Uses the real Flask routes + real email service + real Gmail SMTP, but an
isolated SQLite database so production data is never touched. After sending,
it logs into the inbox over IMAP and confirms the message actually arrived.

Run:  python demo_email_delivery.py
"""

import os
import time
import imaplib
import tempfile

from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

from models import (
    db, Owner, Shop, Customer, Conversation, PendingQuestion, EmailDelivery
)
from routes.authentication import auth_bp
from routes.shop import shop_bp
from routes.knowledge import knowledge_bp
from routes.customer import customer_bp
from routes.owner import owner_bp

DEMO_INBOX = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
DEMO_CUSTOMER_PASSWORD = "demo-customer-password-123"

if not DEMO_INBOX or not GMAIL_APP_PASSWORD:
    raise SystemExit("GMAIL_ADDRESS / GMAIL_APP_PASSWORD must be set in .env")

tmp_db = os.path.join(tempfile.gettempdir(), "shop_faq_demo.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI="sqlite:///" + tmp_db,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY="demo-secret",
    TESTING=True,
)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(owner_id):
    return db.session.get(Owner, int(owner_id))


for bp in (auth_bp, shop_bp, knowledge_bp, customer_bp, owner_bp):
    app.register_blueprint(bp)


@app.route("/")
def home():
    return "Demo home"


def banner(text):
    print("\n" + "=" * 70 + "\n" + text + "\n" + "=" * 70, flush=True)


def make_shop(owner, token):
    shop = Shop(
        shop_name=token,
        shop_slug=token.lower(),
        owner_id=owner.id,
    )
    db.session.add(shop)
    db.session.commit()
    return shop


def customer_asks(shop, question):
    """Register a customer (real inbox) and ask a question via real routes."""
    client = app.test_client()
    r = client.post(
        f"/s/{shop.shop_slug}",
        data={
            "first_name": "Demo",
            "last_name": "Customer",
            "email": DEMO_INBOX,
            "password": DEMO_CUSTOMER_PASSWORD,
            "confirm_password": DEMO_CUSTOMER_PASSWORD,
        },
        follow_redirects=True,
    )
    assert r.status_code == 200, r.status_code
    r = client.post(
        f"/chat/{shop.shop_slug}",
        data={"question": question},
        follow_redirects=True,
    )
    assert r.status_code == 200, r.status_code
    pending = (
        PendingQuestion.query.filter_by(shop_id=shop.id, status="Pending")
        .order_by(PendingQuestion.id.desc())
        .first()
    )
    assert pending is not None, "Expected a pending question"
    return pending


def owner_answers(owner_email, password, pending, answer):
    client = app.test_client()
    r = client.post(
        "/login",
        data={"email": owner_email, "password": password},
        follow_redirects=True,
    )
    assert r.status_code == 200
    r = client.post(
        f"/answer-question/{pending.id}",
        data={"owner_answer": answer},
        follow_redirects=True,
    )
    assert r.status_code == 200
    return (
        EmailDelivery.query.filter_by(pending_question_id=pending.id)
        .order_by(EmailDelivery.id.desc())
        .first()
    )


def find_in_inbox(token, timeout=60):
    """Poll the REAL inbox over IMAP until the answer email arrives."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            imap.login(DEMO_INBOX, GMAIL_APP_PASSWORD)
            imap.select("INBOX")
            typ, data = imap.search(None, "SUBJECT", f'"Answer from {token}"')
            ids = data[0].split()
            if ids:
                typ, msg_data = imap.fetch(ids[-1], "(RFC822)")
                import email as email_lib
                msg = email_lib.message_from_bytes(msg_data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(
                                "utf-8", "replace"
                            )
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", "replace")
                imap.logout()
                return {
                    "from": msg.get("From"),
                    "to": msg.get("To"),
                    "subject": msg.get("Subject"),
                    "date": msg.get("Date"),
                    "body": body.strip(),
                }
            imap.logout()
        except Exception as exc:
            print("IMAP poll error:", exc, flush=True)
        time.sleep(3)
    return None


def main():
    with app.app_context():
        db.create_all()

        owner = Owner(
            name="Demo Owner",
            email="owner@demo.local",
            password=generate_password_hash("demo-password-123"),
        )
        db.session.add(owner)
        db.session.commit()

        banner("PART 1 - REAL DELIVERY TO A REAL INBOX")
        token_a = f"DemoShop{int(time.time())}"
        shop_a = make_shop(owner, token_a)
        print(f"Shop: {token_a} | customer inbox: {DEMO_INBOX}")
        pending_a = customer_asks(shop_a, "Do you offer gift wrapping?")
        print(f"Customer question became pending question #{pending_a.id}")

        answer_text = "Yes! We offer free gift wrapping on every order."
        delivery_a = owner_answers(
            owner.email, "demo-password-123", pending_a, answer_text
        )
        print(
            f"EmailDelivery #{delivery_a.id}: status={delivery_a.status} "
            f"attempts={delivery_a.attempts} provider_id={delivery_a.provider_email_id}"
        )
        assert delivery_a.status == "Sent", "Email should be Sent"

        print("Checking the REAL inbox over IMAP ...")
        found = find_in_inbox(token_a)
        assert found, "Email did NOT arrive in the real inbox"
        print("INBOX RECEIPT CONFIRMED:")
        print("  From:    ", found["from"])
        print("  To:      ", found["to"])
        print("  Subject: ", found["subject"])
        print("  Date:    ", found["date"])
        print("  Body:    ", found["body"].replace("\n", " ")[:200])
        assert answer_text in found["body"], "Answer text missing from email"

        banner("PART 2 - FAILURE IS SAVED, THEN RETRY SUCCEEDS")
        token_b = f"RetryShop{int(time.time())}"
        shop_b = make_shop(owner, token_b)
        pending_b = customer_asks(shop_b, "What are your opening hours?")

        print("Simulating a provider failure (invalid Gmail app password) ...")
        os.environ["GMAIL_APP_PASSWORD"] = "invalid-password-for-demo"
        delivery_b = owner_answers(
            owner.email,
            "demo-password-123",
            pending_b,
            "We are open 9am to 9pm every day.",
        )
        print(
            f"EmailDelivery #{delivery_b.id}: status={delivery_b.status} "
            f"attempts={delivery_b.attempts}"
        )
        print(f"Saved failure reason: {delivery_b.last_error}")
        assert delivery_b.status == "Failed", "Failure should be recorded"
        assert delivery_b.attempts >= 2, "Automatic retries should have run"
        assert delivery_b.last_error, "Failure reason should be saved"

        print("\nRestoring credentials and retrying via the real retry route ...")
        os.environ["GMAIL_APP_PASSWORD"] = GMAIL_APP_PASSWORD
        client = app.test_client()
        client.post(
            "/login",
            data={"email": owner.email, "password": "demo-password-123"},
            follow_redirects=True,
        )
        r = client.post(
            f"/retry-email/{delivery_b.id}", follow_redirects=True
        )
        assert r.status_code == 200
        delivery_b = db.session.get(EmailDelivery, delivery_b.id)
        print(
            f"After retry -> status={delivery_b.status} "
            f"attempts={delivery_b.attempts} provider_id={delivery_b.provider_email_id}"
        )
        assert delivery_b.status == "Sent", "Retry should succeed"

        print("Checking the REAL inbox for the retried email ...")
        found_b = find_in_inbox(token_b)
        assert found_b, "Retried email did NOT arrive in the real inbox"
        print("RETRIED EMAIL RECEIPT CONFIRMED:")
        print("  Subject: ", found_b["subject"])
        print("  Date:    ", found_b["date"])

        banner("ALL CHECKS PASSED - REAL INBOX DELIVERY + FAILURE SAVE + RETRY")


if __name__ == "__main__":
    main()
