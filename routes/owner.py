
import os
import resend

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
    KnowledgeBase
)

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

        if conversation is None:
            continue

        customer = db.session.get(
            Customer, conversation.customer_id
        )

        if customer is None:
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

    # Save owner's answer
    conversation.ai_answer = answer

    pending.owner_answer = answer
    pending.status = "Answered"
    pending.answered_at = datetime.utcnow()

    # Save approved answer to this shop's Knowledge Base
    knowledge = KnowledgeBase(
        shop_id=shop.id,
        content=(
            f"Question: {conversation.question}\n"
            f"Answer: {answer}"
        )
    )

    db.session.add(knowledge)
    db.session.commit()

    # 3. Send email using Resend API
    try:

        resend_api_key = os.getenv("RESEND_API_KEY")
        resend_from_email = os.getenv("RESEND_FROM_EMAIL")

        if not resend_api_key or not resend_from_email:
            raise ValueError("Resend settings are missing.")

        resend.api_key = resend_api_key

        params = {
            "from": resend_from_email,
            "to": [customer.email],
            "subject": f"Answer from {shop.shop_name}",
            "text": (
                f"Hi {customer.first_name},\n\n"
                f"Your question: {conversation.question}\n\n"
                f"Answer: {answer}\n\n"
                f"Thank you for contacting {shop.shop_name}!"
            ),
            "html": f"""
                <h2>Hi {escape(customer.first_name)}, your question has been answered!</h2>

                <p><strong>Your question:</strong></p>
                <p>{escape(conversation.question)}</p>

                <p><strong>Answer:</strong></p>
                <p>{escape(answer)}</p>

                <p>Thank you for contacting {escape(shop.shop_name)}!</p>
            """
        }

        response = resend.Emails.send(params)

        print("Resend email response:", response)

        flash("Answer saved and email sent successfully!")

    except Exception as e:

        print("Resend email error:", repr(e))

        flash("Answer saved, but email could not be sent.")

    return redirect(
        url_for("owner.pending_questions", shop_id=shop.id)
    )


# 4. Owner Rate Answers page
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


# 5. Owner rates an AI answer
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

        # Save correction to this shop's Knowledge Base
        knowledge = KnowledgeBase(
            shop_id=shop.id,
            content=(
                f"Question: {conversation.question}\n"
                f"Answer: {correct_answer}"
            )
        )

        db.session.add(knowledge)
        db.session.commit()

        flash("Correction saved to the shop knowledge base!")

    else:

        flash("Invalid rating!")

    return redirect(
        url_for("owner.rate_answers", shop_id=shop.id)
    )
