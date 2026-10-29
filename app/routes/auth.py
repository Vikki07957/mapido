from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func, select

from app.extensions import db
from app.forms import LoginForm, RegisterForm
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if db.session.scalar(select(User.id).where(func.lower(User.email) == email)):
            form.email.errors.append("An account already uses this email address.")
        else:
            user = User(name=form.name.data.strip(), email=email, phone=(form.phone.data or "").strip() or None, role=form.role.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user, fresh=True)
            flash("Your MAPIDO account is ready.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("register.html", form=form, title="Create account")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(select(User).where(func.lower(User.email) == email))
        if not user or user.is_suspended or not user.check_password(form.password.data):
            flash("Email or password is incorrect, or this account is unavailable.", "danger")
        else:
            login_user(user, fresh=True)
            flash(f"Welcome back, {user.name}.", "success")
            target = request.args.get("next", "")
            if target.startswith("/") and not target.startswith("//"):
                return redirect(target)
            return redirect(url_for("main.dashboard"))
    return render_template("login.html", form=form, title="Log in")


@auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))