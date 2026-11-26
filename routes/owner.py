
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from html import escape

from models import (
    db,
    Shop,
    PendingQuestion,
    Conversation,
    Customer,
    KnowledgeBase,
    EmailDelivery
)
from email_service import send_answer_email

owner_bp = Blueprint("owner", __name__)

UNKNOWN_MESSAGE = "Thank you! The shop owner will reply to you soon by email."


# 1. Owner views pending questions
@owner_bp.route("/pending-questions/<int:shop_id>")
@login_required
def pending_questions(shop_id):

    shop = Shop.query.filter_by(
        id=shop_id,
        owner_id=current_user.id
    ).first()

    if shop is None:
        return "Shop not found", 404

    pending = PendingQuestion.query.filter_by(
        shop_id=shop.id,
        status="Pending"
    ).all()

    questions = []

    for item in pending:

        conversation = db.session.get(
            Conversation, item.conversation_id
        )

        if conversation is None or conversation.shop_id != shop.id:
            continue

        customer = db.session.get(
            Customer, conversation.customer_id
        )

        if customer is None or customer.shop_id != shop.id:
            continue

        questions.append({
            "pending_id": item.id,
            "question": conversation.question,
            "customer_name": (
                customer.first_name + " " + customer.last_name
            ),
            "customer_email": customer.email
        })

    return render_template(
        "pending_questions.html",
        shop=shop,
        questions=questions
    )


# 2. Owner answers pending question
@owner_bp.route("/answer-question/<int:pending_id>", methods=["POST"])
@login_required
def answer_question(pending_id):

    pending = db.session.get(PendingQuestion, pending_id)

    if pending is None:
        return "Question not found", 404

    shop = Shop.query.filter_by(
        id=pending.shop_id,
        owner_id=current_user.id
    ).first()

    if shop is None:
        return "Unauthorized", 403

    if pending.status != "Pending":
        flash("This question has already been answered!")
        return redirect(
            url_for("owner.pending_questions", shop_id=shop.id)
        )

    answer = request.form.get("owner_answer", "").strip()

    if not answer:
        flash("Please enter an answer!")
        return redirect(
            url_for("owner.pending_questions", shop_id=shop.id)
        )

    conversation = db.session.get(
        Conversation, pending.conversation_id
    )

    if conversation is None or conversation.shop_id != shop.id:
        return "Conversation not found", 404

    customer = db.session.get(
        Customer, conversation.customer_id
    )

    if customer is None or customer.shop_id != shop.id:
        return "Customer not found", 404

    # Save owner's answer.
    conversation.ai_answer = answer
    pending.owner_answer = answer
    pending.status = "Answered"
    pending.answered_at = datetime.utcnow()

    # Save approved answer to this shop's Knowledge Base.
    KnowledgeBase.add_if_missing(
        shop.id,
        f"Question: {conversation.question}\nAnswer: {answer}"
    )

    # Create a persistent email record BEFORE attempting delivery.
    email_text = (
        f"Hi {customer.first_name},\n\n"
        f"Your question: {conversation.question}\n\n"
        f"Answer: {answer}\n\n"
        f"Thank you for contacting {shop.shop_name}!"
    )

    email_html = f"""
        <h2>Hi {escape(customer.first_name)}, your question has been answered!</h2>
        <p><strong>Your question:</strong></p>
        <p>{escape(conversation.question)}</p>
        <p><strong>Answer:</strong></p>
        <p>{escape(answer)}</p>
        <p>Thank you for contacting {escape(shop.shop_name)}!</p>
    """

    delivery = EmailDelivery(
        shop_id=shop.id,
        pending_question_id=pending.id,
        conversation_id=conversation.id,
        recipient=customer.email,
        subject=f"Answer from {shop.shop_name}",
        text_body=email_text,
        html_body=email_html,
        status="Pending",
        attempts=0
    )

    db.session.add(delivery)
    db.session.commit()

    # Attempt real email delivery.
    success = send_answer_email(delivery)

    if success:
        flash(
            "Answer saved. The email provider accepted the message; "
            "delivery to the customer's inbox is not guaranteed."
        )
    else:
        flash(
            "Answer saved, but email delivery failed after automatic "
            "retries. The failure was recorded and you can retry it "
            "from the email delivery page."
        )

    return redirect(
        url_for("owner.email_deliveries", shop_id=shop.id)
    )


# 3. Owner views email delivery history
@owner_bp.route("/email-deliveries/<int:shop_id>")
@login_required
def email_deliveries(shop_id):

    shop = Shop.query.filter_by(
        id=shop_id,
        owner_id=current_user.id
    ).first()

    if shop is None:
        return "Shop not found", 404

    deliveries = EmailDelivery.query.filter_by(
        shop_id=shop.id
    ).order_by(
        EmailDelivery.id.desc()
    ).all()

    return render_template(
        "email_deliveries.html",
        shop=shop,
        deliveries=deliveries
    )


# 4. Owner retries a failed email
@owner_bp.route(
    "/retry-email/<int:delivery_id>",
    methods=["POST"]
)
@login_required
def retry_email(delivery_id):

    delivery = EmailDelivery.query.filter_by(
        id=delivery_id
    ).first()

    if delivery is None:
        return "Email record not found", 404

    shop = Shop.query.filter_by(
        id=delivery.shop_id,
        owner_id=current_user.id
    ).first()

    if shop is None:
        return "Unauthorized", 403

    if delivery.status != "Failed":
        flash("Only failed emails can be retried.")
        return redirect(
            url_for("owner.email_deliveries", shop_id=shop.id)
        )

    success = send_answer_email(delivery)

    if success:
        flash(
            "Email retry was accepted by the provider; delivery to the "
            "customer's inbox is not guaranteed."
        )
    else:
        flash("Email retry failed. The failure has been recorded.")

    return redirect(
        url_for("owner.email_deliveries", shop_id=shop.id)
    )


# 5. Owner Rate Answers page
@owner_bp.route("/rate-answers/<int:shop_id>")
@login_required
def rate_answers(shop_id):

    shop = Shop.query.filter_by(
        id=shop_id,
        owner_id=current_user.id
    ).first()

    if shop is None:
        return "Shop not found", 404

    conversations = Conversation.query.filter_by(
        shop_id=shop.id
    ).order_by(
        Conversation.id.desc()
    ).all()

    return render_template(
        "rate_answers.html",
        shop=shop,
        conversations=conversations,
        UNKNOWN_MESSAGE=UNKNOWN_MESSAGE
    )


# 6. Owner rates an AI answer
@owner_bp.route(
    "/owner-rate-answer/<int:conversation_id>",
    methods=["POST"]
)
@login_required
def owner_rate_answer(conversation_id):

    conversation = db.session.get(
        Conversation, conversation_id
    )

    if conversation is None:
        return "Conversation not found", 404

    shop = Shop.query.filter_by(
        id=conversation.shop_id,
        owner_id=current_user.id
    ).first()

    if shop is None:
        return "Unauthorized", 403

    rating = request.form.get("rating")

    if rating == "Good":

        conversation.rating = "Good"
        conversation.correction_reason = None
        conversation.correct_answer = None

        db.session.commit()

        flash("Answer marked as Good!")

    elif rating == "Bad":

        reason = (
            request.form.get("correction_reason")
            or request.form.get("reason")
            or ""
        ).strip()

        correct_answer = request.form.get(
            "correct_answer", ""
        ).strip()

        if not reason or not correct_answer:
            flash("Please provide the reason and correct answer!")
            return redirect(
                url_for("owner.rate_answers", shop_id=shop.id)
            )

        conversation.rating = "Bad"
        conversation.correction_reason = reason
        conversation.correct_answer = correct_answer

        KnowledgeBase.add_if_missing(
            shop.id,
            f"Question: {conversation.question}\nAnswer: {correct_answer}"
        )
        db.session.commit()

        flash("Correction saved to the shop knowledge base!")

    else:

        flash("Invalid rating!")

    return redirect(
        url_for("owner.rate_answers", shop_id=shop.id)
    )
