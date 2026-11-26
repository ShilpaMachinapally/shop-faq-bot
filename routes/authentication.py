from urllib.parse import urlsplit

from sqlalchemy import func
from flask import Blueprint, render_template, request, redirect, url_for, flash,session

from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Customer, Owner

auth_bp = Blueprint("auth", __name__)


def _safe_next_page(target):
    if not target:
        return None

    parsed = urlsplit(target)

    if parsed.netloc or not parsed.path.startswith("/") or target == "/":
        return None

    return target


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("home", welcome=1))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please complete all fields.")
            return redirect(url_for("auth.signup"))
        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("auth.signup"))
        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for("auth.signup"))
        if Owner.query.filter_by(email=email).first():
            flash("Email already registered!")
            return redirect(url_for("auth.signup"))

        owner = Owner(
            name=name,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(owner)
        db.session.commit()
        login_user(owner)
        flash("Registration successful!")
        return redirect(url_for("home", welcome=1))

    return render_template("signup.html")



@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_page = _safe_next_page(
        request.form.get("next") or request.args.get("next")
    )

    if request.method == "POST":
        email = (
            request.form.get("email")
            or request.form.get("username")
            or ""
        ).strip().lower()

        password = request.form.get("password", "")

        owner = Owner.query.filter(
            func.lower(Owner.email) == email
        ).first()

        if owner and check_password_hash(owner.password, password):
            session.pop("customer_id", None)
            session.pop("shop_id", None)
            session.pop("shop_slug", None)

            login_user(owner)
            flash("Login successful!")
            return redirect(next_page or url_for("home", welcome=1))

        if not owner and Customer.query.filter(
            func.lower(Customer.email) == email
        ).first():
            flash(
                "This email is registered as a customer. "
                "Sign up as an owner to log in."
            )
        else:
            flash("Invalid email or password!")

        if next_page:
            return redirect(url_for("auth.login", next=next_page))

        return redirect(url_for("auth.login"))

    return render_template("login.html")




@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()

    # Clear any customer login remaining in the shared session.
    session.pop("customer_id", None)
    session.pop("shop_id", None)
    session.pop("shop_slug", None)

    # Remove old messages so they don't appear on the login page.
    session.pop("_flashes", None)

    flash("You have been logged out successfully!")
    return redirect(url_for("auth.login"))