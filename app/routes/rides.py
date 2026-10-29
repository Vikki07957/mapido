from datetime import datetime
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms import BookingSeatsForm, RideEditForm, RideForm
from app.models import Notification, PickupPoint, Ride, RideBooking, Vehicle
from app.services.bookings import notify, request_seats, update_booking_status

rides_bp = Blueprint("rides", __name__)


def driver_required():
    if current_user.role != "driver":
        flash("Only driver accounts can publish or manage rides.", "danger")
        return False
    return True


def save_pickups(ride, text):
    ride.pickup_points.clear()
    for order, label in enumerate([line.strip()[:120] for line in text.splitlines() if line.strip()][:8], 1):
        ride.pickup_points.append(PickupPoint(label=label, sequence_no=order))


@rides_bp.route("/offer", methods=["GET", "POST"])
@login_required
def offer():
    if not driver_required():
        return redirect(url_for("main.dashboard"))
    form = RideForm()
    if form.validate_on_submit():
        if form.origin.data.strip().casefold() == form.destination.data.strip().casefold() or form.travel_date.data < datetime.now().date():
            flash("Choose two different locations and a date that is today or later.", "danger")
        else:
            try:
                vehicle = db.session.scalar(select(Vehicle).where(Vehicle.user_id == current_user.id))
                if vehicle:
                    vehicle.model = form.vehicle.data.strip()
                    vehicle.registration_number = form.registration.data.strip()
                else:
                    vehicle = Vehicle(user_id=current_user.id, model=form.vehicle.data.strip(), registration_number=form.registration.data.strip())
                    db.session.add(vehicle)
                    db.session.flush()
                ride = Ride(driver_id=current_user.id, vehicle_id=vehicle.id, origin=form.origin.data.strip(), destination=form.destination.data.strip(), travel_date=form.travel_date.data, departure_time=form.departure_time.data, total_seats=form.seats.data, estimated_cost=Decimal(form.estimated_cost.data), notes=(form.notes.data or "").strip() or None)
                save_pickups(ride, form.pickup_points.data or "")
                db.session.add(ride)
                db.session.commit()
                flash("Ride published.", "success")
                return redirect(url_for("main.dashboard"))
            except Exception:
                db.session.rollback()
                raise
    return render_template("offer.html", form=form, title="Offer a ride")


@rides_bp.post("/<int:ride_id>/edit")
@login_required
def edit(ride_id):
    if not driver_required():
        return redirect(url_for("main.dashboard"))
    ride = db.session.execute(select(Ride).where(Ride.id == ride_id).with_for_update()).scalar_one_or_none()
    if not ride or ride.driver_id != current_user.id or ride.status != "Open":
        flash("This ride is not available to edit.", "danger")
        return redirect(url_for("main.dashboard"))
    form = RideEditForm()
    if form.validate_on_submit():
        confirmed = db.session.scalar(select(func.coalesce(func.sum(RideBooking.seats), 0)).where(RideBooking.ride_id == ride.id, RideBooking.status == "Confirmed"))
        if form.seats.data < int(confirmed or 0) or form.origin.data.strip().casefold() == form.destination.data.strip().casefold() or form.travel_date.data < datetime.now().date():
            flash("Check the route/date and keep capacity at least as large as confirmed seats.", "danger")
        else:
            ride.origin = form.origin.data.strip()
            ride.destination = form.destination.data.strip()
            ride.travel_date = form.travel_date.data
            ride.departure_time = form.departure_time.data
            ride.total_seats = form.seats.data
            ride.estimated_cost = Decimal(form.estimated_cost.data)
            ride.notes = (form.notes.data or "").strip() or None
            save_pickups(ride, form.pickup_points.data or "")
            db.session.commit()
            flash("Ride updated.", "success")
    else:
        flash("Check the ride details and try again.", "danger")
    return redirect(url_for("main.dashboard"))


@rides_bp.post("/<int:ride_id>/request")
@login_required
def request_booking(ride_id):
    if current_user.role != "passenger":
        flash("Passenger accounts can request seats.", "danger")
        return redirect(url_for("main.find_rides"))
    form = BookingSeatsForm()
    if not form.validate_on_submit():
        flash("Choose a valid number of seats.", "danger")
        return redirect(url_for("main.find_rides"))
    try:
        request_seats(ride_id, current_user, form.seats.data)
        flash("Seat request sent to the driver.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "danger")
    except IntegrityError:
        db.session.rollback()
        flash("You already have an active request for this ride.", "danger")
    return redirect(url_for("main.bookings"))


@rides_bp.post("/bookings/<int:booking_id>/status/<status>")
@login_required
def booking_status(booking_id, status):
    try:
        update_booking_status(booking_id, current_user, status.title())
        flash(f"Booking {status.lower()}.", "success")
    except ValueError as error:
        db.session.rollback()
        flash(str(error), "danger")
    return redirect(url_for("main.dashboard"))


@rides_bp.post("/bookings/<int:booking_id>/cancel")
@login_required
def cancel_booking(booking_id):
    booking = db.session.execute(select(RideBooking).where(RideBooking.id == booking_id).with_for_update()).scalar_one_or_none()
    if not booking or booking.passenger_id != current_user.id or booking.status not in {"Pending", "Confirmed"}:
        flash("This booking cannot be cancelled.", "danger")
    else:
        booking.status = "Cancelled"
        notify(booking.ride.driver_id, f"{current_user.name} cancelled a booking on your ride.")
        db.session.commit()
        flash("Booking cancelled; confirmed seats are available again.", "success")
    return redirect(url_for("main.bookings"))


@rides_bp.post("/<int:ride_id>/cancel")
@login_required
def cancel_ride(ride_id):
    if not driver_required():
        return redirect(url_for("main.dashboard"))
    ride = db.session.execute(select(Ride).where(Ride.id == ride_id).with_for_update()).scalar_one_or_none()
    if not ride or ride.driver_id != current_user.id or ride.status != "Open":
        flash("This ride can no longer be cancelled.", "danger")
    else:
        for booking in ride.bookings:
            if booking.status in {"Pending", "Confirmed"}:
                booking.status = "Cancelled"
                notify(booking.passenger_id, "A ride you booked was cancelled by its driver.")
        ride.status = "Cancelled"
        db.session.commit()
        flash("Ride cancelled and riders notified.", "success")
    return redirect(url_for("main.dashboard"))


@rides_bp.post("/<int:ride_id>/complete")
@login_required
def complete_ride(ride_id):
    ride = db.session.execute(select(Ride).where(Ride.id == ride_id).with_for_update()).scalar_one_or_none()
    now = datetime.now()
    if not ride or ride.driver_id != current_user.id or ride.status != "Open" or datetime.combine(ride.travel_date, ride.departure_time) > now:
        flash("Only your rides that have departed can be marked completed.", "danger")
    else:
        ride.status = "Completed"
        for booking in ride.bookings:
            if booking.status == "Confirmed":
                booking.status = "Completed"
        db.session.commit()
        flash("Journey marked completed. Riders can now leave a review.", "success")
    return redirect(url_for("main.dashboard"))


@rides_bp.post("/bookings/<int:booking_id>/review")
@login_required
def review(booking_id):
    from app.forms import ReviewForm
    from app.models import Review

    form = ReviewForm()
    booking = db.session.get(RideBooking, booking_id)
    if not form.validate_on_submit() or not booking or booking.status != "Completed" or booking.ride.status != "Completed":
        flash("Only participants in completed rides can submit a valid review.", "danger")
        return redirect(url_for("main.bookings"))
    if current_user.id == booking.passenger_id:
        target_id = booking.ride.driver_id
    elif current_user.id == booking.ride.driver_id:
        target_id = booking.passenger_id
    else:
        flash("You did not participate in this ride.", "danger")
        return redirect(url_for("main.bookings"))
    db.session.add(Review(ride_id=booking.ride_id, reviewer_id=current_user.id, reviewed_user_id=target_id, rating=form.rating.data, comment=(form.comment.data or "").strip()))
    try:
        db.session.commit()
        flash("Review submitted.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("You have already reviewed this participant for the journey.", "danger")
    return redirect(url_for("profile.profile"))