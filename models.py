

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

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("owners.id"),
        nullable=False
    )





class KnowledgeBase(db.Model):
    __tablename__ = "knowledge_base"

    id = db.Column(db.Integer, primary_key=True)

    shop_id = db.Column(
        db.Integer,
        db.ForeignKey("shops.id"),
        nullable=False
    )

    content = db.Column(db.Text, nullable=False)


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)

    shop_id = db.Column(
        db.Integer,
        db.ForeignKey("shops.id"),
        nullable=False
    )

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)



    
class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)

    shop_id = db.Column(
        db.Integer,
        db.ForeignKey("shops.id"),
        nullable=False
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        nullable=False
    )

    question = db.Column(db.Text, nullable=False)
    ai_answer = db.Column(db.Text)
    rating = db.Column(db.String(20))
    correction_reason = db.Column(db.Text)
    correct_answer = db.Column(db.Text)




    
class PendingQuestion(db.Model):
    __tablename__ = "pending_questions"

    id = db.Column(db.Integer, primary_key=True)

    shop_id = db.Column(
        db.Integer,
        db.ForeignKey("shops.id"),
        nullable=False
    )

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("conversations.id"),
        nullable=False
    )

    owner_answer = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending")
    answered_at = db.Column(db.DateTime)

