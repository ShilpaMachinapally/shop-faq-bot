

import re
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Create SQLAlchemy object
db = SQLAlchemy()


class Owner(UserMixin, db.Model):
    __tablename__ = "owners"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


class Shop(db.Model):
    __tablename__ = "shops"

    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(150), nullable=False)
    shop_slug = db.Column(db.String(150), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("owners.id"), nullable=False)


class KnowledgeBase(db.Model):
    __tablename__ = "knowledge_base"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)

    @staticmethod
    def normalize_content(content):
        if not content:
            return ""

        lines = []
        for line in content.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            line = re.sub(
                r"^(?:q|question)\s*[:.]\s*", "Question: ", line,
                flags=re.IGNORECASE
            )
            line = re.sub(
                r"^(?:a|answer)\s*[:.]\s*", "Answer: ", line,
                flags=re.IGNORECASE
            )
            if line:
                lines.append(line)

        return "\n".join(lines).casefold()

    @classmethod
    def add_if_missing(cls, shop_id, content):
        normalized = cls.normalize_content(content)
        if not normalized:
            return None

        for entry in cls.query.filter_by(shop_id=shop_id).all():
            if cls.normalize_content(entry.content) == normalized:
                return None

        knowledge = cls(shop_id=shop_id, content=content)
        db.session.add(knowledge)
        return knowledge


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    question = db.Column(db.Text, nullable=False)
    ai_answer = db.Column(db.Text)
    rating = db.Column(db.String(20))
    correction_reason = db.Column(db.Text)
    correct_answer = db.Column(db.Text)


class PendingQuestion(db.Model):
    __tablename__ = "pending_questions"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    owner_answer = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending")
    answered_at = db.Column(db.DateTime)


class EmailDelivery(db.Model):
    """Persist an owner-answer email and its delivery/retry state."""

    __tablename__ = "email_deliveries"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False, index=True)
    pending_question_id = db.Column(
        db.Integer, db.ForeignKey("pending_questions.id"), nullable=False, index=True
    )
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id"), nullable=False, index=True
    )
    recipient = db.Column(db.String(254), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    text_body = db.Column(db.Text, nullable=False)
    html_body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    provider_email_id = db.Column(db.String(255))
    last_error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    sent_at = db.Column(db.DateTime)
