from datetime import date

from sqlalchemy import func, select

from app.extensions import db
from app.models import Notification, Ride, RideBooking


def notify(user_id, message):
    db.session.add(Notification(user_id=user_id, message=message))


def request_seats(ride_id, passenger, seats):
    ride = db.session.execute(select(Ride).where(Ride.id == ride_id).with_for_update()).scalar_one_or_none()
    if not ride or ride.is_sample or ride.status != "Open" or ride.travel_date < date.today() or ride.driver_id == passenger.id:
        raise ValueError("This ride is no longer available.")
    confirmed = db.session.scalar(select(func.coalesce(func.sum(RideBooking.seats), 0)).where(
        RideBooking.ride_id == ride.id, RideBooking.status == "Confirmed"
    ))
    if seats > ride.total_seats - int(confirmed or 0):
        raise ValueError("Not enough seats remain for this request.")
    duplicate = db.session.scalar(select(RideBooking.id).where(
        RideBooking.ride_id == ride.id,
        RideBooking.passenger_id == passenger.id,
        RideBooking.status.in_(["Pending", "Confirmed"]),
    ))
    if duplicate:
        raise ValueError("You already have an active request for this ride.")
    booking = RideBooking(ride_id=ride.id, passenger_id=passenger.id, seats=seats, status="Pending")
    db.session.add(booking)
    notify(ride.driver_id, f"{passenger.name} requested seats on your ride.")
    db.session.commit()
    return booking


def update_booking_status(booking_id, driver, status):
    ride_id = db.session.scalar(select(RideBooking.ride_id).where(RideBooking.id == booking_id))
    if not ride_id:
        raise ValueError("This booking request is no longer available.")
    ride = db.session.execute(select(Ride).where(Ride.id == ride_id).with_for_update()).scalar_one_or_none()
    booking = db.session.execute(select(RideBooking).where(RideBooking.id == booking_id).with_for_update()).scalar_one_or_none()
    if not booking or not ride or booking.status != "Pending" or ride.driver_id != driver.id or ride.status != "Open":
        raise ValueError("This booking request is no longer pending on your open ride.")
    if status not in {"Confirmed", "Rejected"}:
        raise ValueError("Invalid booking status.")
    if status == "Confirmed":
        confirmed = db.session.scalar(select(func.coalesce(func.sum(RideBooking.seats), 0)).where(
            RideBooking.ride_id == ride.id, RideBooking.status == "Confirmed"
        ))
        if int(confirmed or 0) + booking.seats > ride.total_seats:
            raise ValueError("Not enough seats remain for this request.")
    booking.status = status
    notify(booking.passenger_id, f"Your booking was {status.lower()}.")
    db.session.commit()
    return booking