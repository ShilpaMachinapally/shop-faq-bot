import os
import re
import smtplib
import time

from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid, formatdate

import resend

from models import db, EmailDelivery


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MAX_AUTOMATIC_ATTEMPTS = 3


def _validate_recipient(delivery):
    recipient = (delivery.recipient or "").strip()

    if not EMAIL_PATTERN.fullmatch(recipient):
        raise ValueError("Customer email address is missing or invalid.")

    return recipient


def _forced_failure_enabled():
    return (
        os.getenv("EMAIL_FORCE_FAILURE", "false")
        .strip()
        .lower()
        == "true"
    )


def _send_via_gmail(delivery):
    recipient = _validate_recipient(delivery)

    address = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not address or not app_password:
        raise ValueError(
            "GMAIL_ADDRESS or GMAIL_APP_PASSWORD is missing."
        )

    message = EmailMessage()
    message["From"] = address
    message["To"] = recipient
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
    recipient = _validate_recipient(delivery)

    test_mode = (
        os.getenv("RESEND_TEST_MODE", "true").strip().lower() == "true"
    )

    if test_mode:
        raise RuntimeError(
            "Resend test mode is enabled: messages go to "
            "delivered@resend.dev, not to the customer. Set "
            "RESEND_TEST_MODE=false and verify the sender before retrying."
        )

    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL")

    if not api_key:
        raise ValueError("RESEND_API_KEY is missing.")

    if not from_email:
        raise ValueError("RESEND_FROM_EMAIL is missing.")

    resend.api_key = api_key

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
    provider = os.getenv("EMAIL_PROVIDER", "gmail").strip().lower()

    if provider == "gmail":
        return _send_via_gmail(delivery)

    if provider == "resend":
        return _send_via_resend(delivery)

    raise ValueError(f"Unknown EMAIL_PROVIDER: {provider}")


def send_answer_email(delivery):
    """Send a saved email, persist every failure, and retry automatically."""

    if delivery.status == "Sent":
        return False

    try:
        configured_attempts = int(
            os.getenv("EMAIL_MAX_ATTEMPTS", str(MAX_AUTOMATIC_ATTEMPTS))
        )
    except (TypeError, ValueError):
        configured_attempts = MAX_AUTOMATIC_ATTEMPTS

    max_attempts = max(
        1, min(MAX_AUTOMATIC_ATTEMPTS, configured_attempts)
    )

    try:
        backoff_seconds = float(
            os.getenv("EMAIL_RETRY_BACKOFF_SECONDS", "2")
        )
    except (TypeError, ValueError):
        backoff_seconds = 2.0

    backoff_seconds = max(0.0, backoff_seconds)

    for attempt_number in range(1, max_attempts + 1):

        current = db.session.get(EmailDelivery, delivery.id)

        if current is None:
            return False

        if current.status == "Sent":
            return False

        current.attempts += 1
        current.status = "Pending"
        current.updated_at = datetime.utcnow()
        db.session.commit()

        try:
            _validate_recipient(current)

            if _forced_failure_enabled():
                raise RuntimeError(
                    "EMAIL_FORCE_FAILURE=true: intentional email failure "
                    "for testing."
                )

            provider_id = _provider_send(current)

            current.provider_email_id = str(provider_id)
            current.status = "Sent"
            current.sent_at = datetime.utcnow()
            current.last_error = None
            current.updated_at = datetime.utcnow()
            db.session.commit()
            return True

        except Exception as error:
            db.session.rollback()
            current = db.session.get(EmailDelivery, delivery.id)

            if current is None:
                return False

            current.last_error = f"{type(error).__name__}: {error}"
            current.updated_at = datetime.utcnow()

            if attempt_number < max_attempts:
                current.status = "Pending"
            else:
                current.status = "Failed"

            db.session.commit()

            print(
                f"Email attempt {current.attempts} failed: {error}",
                flush=True
            )

            if attempt_number < max_attempts:
                time.sleep(backoff_seconds * (2 ** (attempt_number - 1)))

    return False
