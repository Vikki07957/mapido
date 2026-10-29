from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user

from app.extensions import db
from app.forms import SupportForm
from app.models import Complaint, EmergencyReport

support_bp = Blueprint("support", __name__)


@support_bp.route("/", methods=["GET", "POST"])
def support():
    form = SupportForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated and not form.email.data:
            form.email.errors.append("Enter an email address so support can reply.")
        else:
            email = current_user.email if current_user.is_authenticated else form.email.data.strip().lower()
            complaint = Complaint(user_id=current_user.id if current_user.is_authenticated else None, contact_email=email, kind=form.kind.data, subject=form.subject.data.strip(), body=form.body.data.strip())
            db.session.add(complaint)
            if form.kind.data == "Emergency report":
                db.session.add(EmergencyReport(user_id=current_user.id if current_user.is_authenticated else None, details=f"{form.subject.data.strip()}\n\n{form.body.data.strip()}"))
            db.session.commit()
            flash("Your report was sent to the MAPIDO support team. This form does not contact emergency services.", "success")
            return redirect(url_for("support.support"))
    return render_template("support.html", form=form, title="Support and safety")