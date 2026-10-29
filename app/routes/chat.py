from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, select

from app.extensions import db
from app.forms import MessageForm
from app.models import ChatMessage, Ride, RideBooking, User

chat_bp = Blueprint("chat", __name__)


@chat_bp.get("/")
@login_required
def conversations():
    query = select(RideBooking).join(Ride).where(
        RideBooking.status.in_(["Confirmed", "Completed"]),
        or_(Ride.driver_id == current_user.id, RideBooking.passenger_id == current_user.id),
    ).order_by(RideBooking.updated_at.desc())
    bookings = db.session.scalars(query).all()
    if bookings:
        return redirect(url_for("chat.conversation", booking_id=bookings[0].id))
    return render_template("chat.html", conversations=[], booking_id=None, messages=[], form=MessageForm(), title="Messages")


@chat_bp.route("/<int:booking_id>", methods=["GET", "POST"])
@login_required
def conversation(booking_id):
    booking = db.session.get(RideBooking, booking_id)
    if not booking or booking.status not in {"Confirmed", "Completed"} or current_user.id not in {booking.passenger_id, booking.ride.driver_id}:
        flash("Messages are available to participants with a confirmed or completed ride.", "danger")
        return redirect(url_for("chat.conversations"))
    other_id = booking.passenger_id if booking.ride.driver_id == current_user.id else booking.ride.driver_id
    other = db.session.get(User, other_id)
    form = MessageForm()
    if form.validate_on_submit():
        message = form.body.data.strip()
        if message:
            db.session.add(ChatMessage(booking_id=booking.id, sender_id=current_user.id, body=message))
            booking.updated_at = datetime.now()
            db.session.commit()
            return redirect(url_for("chat.conversation", booking_id=booking.id))
    messages = db.session.scalars(select(ChatMessage).where(ChatMessage.booking_id == booking.id).order_by(ChatMessage.created_at)).all()
    for message in messages:
        if message.sender_id != current_user.id and message.read_at is None:
            message.read_at = datetime.now()
    db.session.commit()
    all_bookings = db.session.scalars(select(RideBooking).join(Ride).where(
        RideBooking.status.in_(["Confirmed", "Completed"]),
        or_(Ride.driver_id == current_user.id, RideBooking.passenger_id == current_user.id),
    ).order_by(RideBooking.updated_at.desc())).all()
    conversations = []
    for item in all_bookings:
        person_id = item.passenger_id if item.ride.driver_id == current_user.id else item.ride.driver_id
        person = db.session.get(User, person_id)
        unread = db.session.scalar(select(db.func.count(ChatMessage.id)).where(ChatMessage.booking_id == item.id, ChatMessage.sender_id != current_user.id, ChatMessage.read_at.is_(None)))
        conversations.append((item, person, unread))
    return render_template("chat.html", conversations=conversations, booking_id=booking.id, messages=messages, other=other, form=form, title="Messages")