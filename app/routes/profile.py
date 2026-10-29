import os
import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from werkzeug.utils import secure_filename

from app.extensions import db
from app.forms import ChangePasswordForm, ProfileForm
from app.models import Review

profile_bp = Blueprint("profile", __name__)
ALLOWED_IMAGES = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()
    if request.method == "POST" and "save_profile" in request.form and form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.phone = (form.phone.data or "").strip() or None
        upload = form.profile_photo.data
        if upload:
            if upload.content_length and upload.content_length > 2 * 1024 * 1024:
                flash("Profile image must be 2 MB or smaller.", "danger")
                return redirect(url_for("profile.profile"))
            try:
                image = Image.open(upload.stream)
                image.verify()
                extension = ALLOWED_IMAGES.get(image.format)
            except (UnidentifiedImageError, OSError):
                extension = None
            if not extension:
                flash("Upload a valid JPEG, PNG or WebP image.", "danger")
                return redirect(url_for("profile.profile"))
            upload.stream.seek(0)
            os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
            filename = secure_filename(f"{uuid.uuid4().hex}{extension}")
            upload.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
            current_user.profile_photo = f"uploads/{filename}"
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile.profile"))
    if request.method == "POST" and "change_password" in request.form and password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash("Password changed.", "success")
            return redirect(url_for("profile.profile"))
    reviews = db.session.scalars(select(Review).where(Review.reviewed_user_id == current_user.id).order_by(Review.created_at.desc())).all()
    return render_template("profile.html", form=form, password_form=password_form, reviews=reviews, title="Profile")


@profile_bp.post("/reviews/<int:review_id>/report")
@login_required
def report_review(review_id):
    review = db.session.get(Review, review_id)
    if not review or review.reviewed_user_id != current_user.id or review.is_reported:
        flash("This review is not available to report.", "danger")
    else:
        review.is_reported = True
        db.session.commit()
        flash("Review reported for administrator review.", "success")
    return redirect(url_for("profile.profile"))