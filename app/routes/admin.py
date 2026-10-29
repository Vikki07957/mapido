from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.extensions import db
from app.models import Complaint, EmergencyReport, Notification, Review, Ride, RideBooking, User

admin_bp = Blueprint("admin", __name__)


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@admin_bp.get("/")
@admin_required
def dashboard():
    users = db.session.scalars(select(User).order_by(User.created_at.desc()).limit(100)).all()
    complaints = db.session.scalars(select(Complaint).order_by(Complaint.created_at.desc()).limit(100)).all()
    reports = db.session.scalars(select(Review).where(Review.is_reported.is_(True)).order_by(Review.created_at.desc()).limit(100)).all()
    rides = db.session.scalars(select(Ride).order_by(Ride.created_at.desc()).limit(100)).all()
    bookings = db.session.scalars(select(RideBooking).order_by(RideBooking.created_at.desc()).limit(100)).all()
    emergencies = db.session.scalars(select(EmergencyReport).order_by(EmergencyReport.created_at.desc()).limit(100)).all()
    stats = {
        "users": db.session.scalar(select(func.count(User.id))) or 0,
        "rides": db.session.scalar(select(func.count(Ride.id))) or 0,
        "bookings": db.session.scalar(select(func.count(RideBooking.id))) or 0,
        "open_reports": sum(item.status == "Open" for item in complaints),
    }
    return render_template("admin.html", users=users, complaints=complaints, reports=reports, rides=rides, bookings=bookings, emergencies=emergencies, stats=stats, title="Admin")


@admin_bp.post("/users/<int:user_id>/suspend")
@admin_required
def suspend_user(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role == "admin" or user.id == current_user.id:
        flash("This account cannot be changed.", "danger")
    else:
        user.is_suspended = bool(int(request.form.get("suspend", "1")))
        db.session.commit()
        flash("Account " + ("suspended." if user.is_suspended else "restored."), "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/complaints/<int:complaint_id>/resolve")
@admin_required
def resolve_complaint(complaint_id):
    complaint = db.session.get(Complaint, complaint_id)
    if complaint and complaint.status == "Open":
        complaint.status = "Resolved"
        complaint.resolved_at = datetime.now()
        db.session.commit()
        flash("Complaint marked resolved.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/reviews/<int:review_id>/resolve")
@admin_required
def resolve_review(review_id):
    review = db.session.get(Review, review_id)
    if review:
        review.is_reported = False
        db.session.commit()
    flash("Review report resolved.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/rides/<int:ride_id>/cancel")
@admin_required
def cancel_ride(ride_id):
    ride = db.session.execute(select(Ride).where(Ride.id == ride_id).with_for_update()).scalar_one_or_none()
    if not ride or ride.status != "Open":
        flash("This ride is not open.", "danger")
    else:
        for booking in ride.bookings:
            if booking.status in {"Pending", "Confirmed"}:
                booking.status = "Cancelled"
                db.session.add(Notification(user_id=booking.passenger_id, message="A MAPIDO administrator cancelled a ride you had booked."))
        ride.status = "Cancelled"
        db.session.commit()
        flash("Ride cancelled and passengers notified.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/bookings/<int:booking_id>/cancel")
@admin_required
def cancel_booking(booking_id):
    booking = db.session.execute(select(RideBooking).where(RideBooking.id == booking_id).with_for_update()).scalar_one_or_none()
    if not booking or booking.status not in {"Pending", "Confirmed"}:
        flash("This booking is no longer active.", "danger")
    else:
        booking.status = "Cancelled"
        db.session.add(Notification(user_id=booking.passenger_id, message="A MAPIDO administrator cancelled your booking."))
        db.session.add(Notification(user_id=booking.ride.driver_id, message="A MAPIDO administrator cancelled a booking on your ride."))
        db.session.commit()
        flash("Booking cancelled and both parties notified.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/emergency/<int:report_id>/review")
@admin_required
def review_emergency(report_id):
    report = db.session.get(EmergencyReport, report_id)
    if report and report.status == "Open":
        report.status = "Reviewed"
        db.session.commit()
    flash("Emergency report marked reviewed. This does not contact emergency services.", "success")
    return redirect(url_for("admin.dashboard"))
