import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Shop

shop_bp = Blueprint("shop", __name__)


def make_unique_slug(shop_name):
    base_slug = re.sub(r"[^a-z0-9]+", "-", shop_name.lower()).strip("-")
    base_slug = base_slug or "my-shop"
    slug = base_slug
    suffix = 2
    while Shop.query.filter_by(shop_slug=slug).first():
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


@shop_bp.route("/create-shop", methods=["GET", "POST"])
@login_required
def create_shop():
    if request.method == "POST":
        shop_name = request.form.get("shop_name", "").strip()
        if not shop_name:
            flash("Please enter a shop name.")
            return redirect(url_for("shop.create_shop"))
        if len(shop_name) > 150:
            flash("Shop name must be 150 characters or fewer.")
            return redirect(url_for("shop.create_shop"))

        shop = Shop(
            shop_name=shop_name,
            shop_slug=make_unique_slug(shop_name),
            owner_id=current_user.id
        )
        db.session.add(shop)
        db.session.commit()
        flash("Shop created successfully!")
        return redirect(url_for("shop.my_shop"))

    return render_template("create_shop.html")


@shop_bp.route("/my-shop")
@login_required
def my_shop():
    shops = Shop.query.filter_by(owner_id=current_user.id).order_by(Shop.id.desc()).all()
    return render_template("my_shop.html", shops=shops)
