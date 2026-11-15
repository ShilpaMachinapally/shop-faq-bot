
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Shop, KnowledgeBase

knowledge_bp = Blueprint("knowledge", __name__)


# Add shop information
@knowledge_bp.route("/add-knowledge/<int:shop_id>", methods=["GET", "POST"])
@login_required
def add_knowledge(shop_id):

    shop = Shop.query.filter_by(
        id=shop_id,
        owner_id=current_user.id
    ).first()

    if shop is None:
        return "Shop not found", 404

    if request.method == "POST":

        content = request.form.get("content")

        if content:

            knowledge = KnowledgeBase(
                shop_id=shop.id,
                content=content
            )

            db.session.add(knowledge)
            db.session.commit()

            flash("Information saved successfully!")

            return redirect(
                url_for("knowledge.add_knowledge", shop_id=shop.id)
            )

        flash("Please enter shop information!")

    return render_template("add_knowledge.html", shop=shop)
