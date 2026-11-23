import os
import smtplib
import time

from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid, formatdate

import resend

from models import db, EmailDelivery


def _send_via_gmail(delivery):
    address = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not address or not app_password:
        raise ValueError(
            "GMAIL_ADDRESS or GMAIL_APP_PASSWORD is missing."
        )

    message = EmailMessage()
    message["From"] = address
    message["To"] = delivery.recipient
    message["Subject"] = delivery.subject
    message["Date"] = formatdate(localtime=True)
    message_id = make_msgid(domain="shop-faq-bot")
    message["Message-ID"] = message_id
    message.set_content(delivery.text_body)
    message.add_alternative(delivery.html_body, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(address, app_password)
        server.send_message(message)

    return message_id


def _send_via_resend(delivery):
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL")

    if not api_key:
        raise ValueError("RESEND_API_KEY is missing.")

    if not from_email:
        raise ValueError("RESEND_FROM_EMAIL is missing.")

    resend.api_key = api_key

    test_mode = (
        os.getenv("RESEND_TEST_MODE", "true").lower() == "true"
    )
    recipient = "delivered@resend.dev" if test_mode else delivery.recipient

    params = {
        "from": from_email,
        "to": [recipient],
        "subject": delivery.subject,
        "text": delivery.text_body,
        "html": delivery.html_body
    }

    response = resend.Emails.send(params)

    if isinstance(response, dict):
        provider_id = response.get("id")
    else:
        provider_id = getattr(response, "id", None)

    if not provider_id:
        raise RuntimeError(
            "Email provider did not return an email ID."
        )

    return str(provider_id)


def _provider_send(delivery):
    provider = os.getenv("EMAIL_PROVIDER", "resend").strip().lower()

    if provider == "gmail":
        return _send_via_gmail(delivery)

    if provider == "resend":
        return _send_via_resend(delivery)

    raise ValueError(f"Unknown EMAIL_PROVIDER: {provider}")


def send_answer_email(delivery):
    """Send a saved email, persist every failure, and retry automatically."""

    max_attempts = max(1, int(os.getenv("EMAIL_MAX_ATTEMPTS", "3")))
    backoff_seconds = float(os.getenv("EMAIL_RETRY_BACKOFF_SECONDS", "2"))

    for attempt_number in range(1, max_attempts + 1):

        delivery.attempts += 1
        delivery.status = "Pending"
        delivery.updated_at = datetime.utcnow()
        db.session.commit()

        try:
            provider_id = _provider_send(delivery)

            delivery.provider_email_id = str(provider_id)
            delivery.status = "Sent"
            delivery.sent_at = datetime.utcnow()
            delivery.last_error = None
            delivery.updated_at = datetime.utcnow()
            db.session.commit()
            return True

        except Exception as error:
            db.session.rollback()
            delivery = db.session.get(EmailDelivery, delivery.id)

            if delivery is None:
                return False

            delivery.last_error = str(error)
            delivery.updated_at = datetime.utcnow()

            if attempt_number < max_attempts:
                delivery.status = "Pending"
            else:
                delivery.status = "Failed"

            db.session.commit()

            print(
                f"Email attempt {delivery.attempts} failed: {error}",
                flush=True
            )

            if attempt_number < max_attempts:
                time.sleep(backoff_seconds * (2 ** (attempt_number - 1)))

    return False
