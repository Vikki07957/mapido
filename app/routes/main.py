from datetime import datetime

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_, select

from app.extensions import db
from app.models import Notification, Review, Ride, RideBooking, User, Vehicle

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    return render_template("home.html", title="Share the Ride, Split the Cost")


@main_bp.get("/rides")
def find_rides():
    query = select(Ride, User, Vehicle).join(User, Ride.driver_id == User.id).outerjoin(Vehicle, Ride.vehicle_id == Vehicle.id)
    query = query.where(Ride.status == "Open", Ride.travel_date >= datetime.now().date(), User.is_suspended.is_(False))
    origin = request.args.get("origin", "").strip()
    destination = request.args.get("destination", "").strip()
    travel_date = request.args.get("date", "").strip()
    time_after = request.args.get("time_after", "").strip()
    min_seats = request.args.get("min_seats", "1").strip()
    max_contribution = request.args.get("max_contribution", "").strip()
    if origin:
        query = query.where(Ride.origin.ilike(f"%{origin[:100]}%"))
    if destination:
        query = query.where(Ride.destination.ilike(f"%{destination[:100]}%"))
    try:
        if travel_date:
            parsed_date = datetime.strptime(travel_date, "%Y-%m-%d").date()
            query = query.where(Ride.travel_date == parsed_date)
    except ValueError:
        travel_date = ""
    try:
        if time_after:
            parsed_time = datetime.strptime(time_after, "%H:%M").time()
            query = query.where(Ride.departure_time >= parsed_time)
    except ValueError:
        time_after = ""
    try:
        minimum = min(8, max(1, int(min_seats or 1)))
    except ValueError:
        minimum = 1
    confirmed = select(func.coalesce(func.sum(RideBooking.seats), 0)).where(
        RideBooking.ride_id == Ride.id, RideBooking.status == "Confirmed"
    ).correlate(Ride).scalar_subquery()
    query = query.where((Ride.total_seats - confirmed) >= minimum)
    if max_contribution:
        try:
            cap = max(0, float(max_contribution))
            query = query.where(Ride.estimated_cost / Ride.total_seats <= cap)
        except ValueError:
            max_contribution = ""
    rides = db.session.execute(query.order_by(Ride.travel_date, Ride.departure_time).limit(50)).all()
    rows = []
    for ride, driver, vehicle in rides:
        left = ride.total_seats - int(db.session.scalar(select(func.coalesce(func.sum(RideBooking.seats), 0)).where(
            RideBooking.ride_id == ride.id, RideBooking.status == "Confirmed"
        )) or 0)
        rating = db.session.scalar(select(func.avg(Review.rating)).where(Review.reviewed_user_id == driver.id))
        rows.append({"ride": ride, "driver": driver, "vehicle": vehicle, "seats_left": left, "rating": rating})
    return render_template("find.html", rides=rows, filters={"origin": origin, "destination": destination, "date": travel_date, "time_after": time_after, "min_seats": minimum, "max_contribution": max_contribution}, title="Find a ride")


@main_bp.get("/dashboard")
@login_required
def dashboard():
    booking_query = select(RideBooking).join(Ride).where(or_(RideBooking.passenger_id == current_user.id, Ride.driver_id == current_user.id))
    bookings = db.session.scalars(booking_query.order_by(Ride.travel_date.desc(), Ride.departure_time.desc()).limit(40)).all()
    rides = db.session.scalars(select(Ride).where(Ride.driver_id == current_user.id).order_by(Ride.travel_date.desc()).limit(20)).all()
    notifications = db.session.scalars(select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(8)).all()
    return render_template("dashboard.html", bookings=bookings, rides=rides, notifications=notifications, title="Dashboard")


@main_bp.get("/bookings")
@login_required
def bookings():
    query = select(RideBooking).join(Ride).where(or_(RideBooking.passenger_id == current_user.id, Ride.driver_id == current_user.id))
    items = db.session.scalars(query.order_by(Ride.travel_date.desc(), RideBooking.created_at.desc()).limit(100)).all()
    return render_template("bookings.html", bookings=items, title="My bookings")