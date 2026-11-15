from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Owner

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

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
        flash("Registration successful! Please log in.")
        return redirect(url_for("auth.login"))

    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        owner = Owner.query.filter_by(email=email).first()

        if owner and check_password_hash(owner.password, password):
            login_user(owner)
            flash("Login successful!")
            return redirect(url_for("home"))

        flash("Invalid email or password!")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully!")
    return redirect(url_for("auth.login"))
