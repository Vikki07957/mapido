from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Computed, Enum, Index, UniqueConstraint, func
from sqlalchemy.dialects import mysql

from app.extensions import db

BIGINT = db.BigInteger().with_variant(db.Integer(), "sqlite").with_variant(mysql.BIGINT(unsigned=True), "mysql")
INTEGER = db.Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(BIGINT, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(190), nullable=False, unique=True)
    phone = db.Column(db.String(30))
    profile_photo = db.Column(db.String(255))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(Enum("driver", "passenger", "admin", name="user_role"), nullable=False, default="passenger")
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    is_suspended = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    vehicle = db.relationship("Vehicle", back_populates="user", uselist=False)

    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        from werkzeug.security import check_password_hash

        if self.password_hash.startswith(("$2a$", "$2b$", "$2y$")):
            import bcrypt

            compatible_hash = self.password_hash.replace("$2y$", "$2b$", 1).encode("ascii")
            return bcrypt.checkpw(password.encode("utf-8"), compatible_hash)
        return check_password_hash(self.password_hash, password)


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id = db.Column(BIGINT, primary_key=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    model = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    user = db.relationship("User", back_populates="vehicle")


class Ride(db.Model):
    __tablename__ = "rides"
    __table_args__ = (
        db.CheckConstraint("total_seats BETWEEN 1 AND 8", name="chk_ride_seats"),
        db.CheckConstraint("estimated_cost >= 0", name="chk_ride_cost"),
        Index("idx_ride_search", "status", "travel_date", "origin", "destination"),
    )

    id = db.Column(BIGINT, primary_key=True)
    driver_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    vehicle_id = db.Column(BIGINT, db.ForeignKey("vehicles.id", ondelete="SET NULL"))
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    travel_date = db.Column(db.Date, nullable=False)
    departure_time = db.Column(db.Time, nullable=False)
    total_seats = db.Column(db.SmallInteger, nullable=False)
    estimated_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    notes = db.Column(db.String(1000))
    status = db.Column(Enum("Open", "Completed", "Cancelled", name="ride_status"), nullable=False, default="Open")
    is_sample = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    driver = db.relationship("User", foreign_keys=[driver_id])
    vehicle = db.relationship("Vehicle")
    bookings = db.relationship("RideBooking", back_populates="ride", cascade="all, delete-orphan")
    pickup_points = db.relationship("PickupPoint", back_populates="ride", cascade="all, delete-orphan", order_by="PickupPoint.sequence_no")


class RideBooking(db.Model):
    __tablename__ = "ride_bookings"
    __table_args__ = (
        db.CheckConstraint("seats BETWEEN 1 AND 8", name="chk_booking_seats"),
        Index("idx_booking_ride_status", "ride_id", "status"),
        Index("idx_booking_passenger", "passenger_id", "status"),
        UniqueConstraint("ride_id", "active_passenger_id", name="uq_active_booking"),
    )

    id = db.Column(BIGINT, primary_key=True)
    ride_id = db.Column(BIGINT, db.ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    passenger_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    seats = db.Column(db.SmallInteger, nullable=False, default=1)
    status = db.Column(Enum("Pending", "Confirmed", "Rejected", "Completed", "Cancelled", name="booking_status"), nullable=False, default="Pending")
    active_passenger_id = db.Column(
        BIGINT,
        Computed("CASE WHEN status IN ('Pending','Confirmed') THEN passenger_id ELSE NULL END", persisted=True),
    )
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    ride = db.relationship("Ride", back_populates="bookings")
    passenger = db.relationship("User", foreign_keys=[passenger_id])
    messages = db.relationship("ChatMessage", back_populates="booking", cascade="all, delete-orphan")


class PickupPoint(db.Model):
    __tablename__ = "pickup_points"
    __table_args__ = (UniqueConstraint("ride_id", "sequence_no", name="uq_pickup_sequence"),)

    id = db.Column(BIGINT, primary_key=True)
    ride_id = db.Column(BIGINT, db.ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    label = db.Column(db.String(120), nullable=False)
    sequence_no = db.Column(db.SmallInteger, nullable=False)
    ride = db.relationship("Ride", back_populates="pickup_points")


class Contribution(db.Model):
    __tablename__ = "payments_or_contributions"
    __table_args__ = (db.CheckConstraint("amount >= 0", name="chk_contribution_amount"),)

    id = db.Column(BIGINT, primary_key=True)
    booking_id = db.Column(BIGINT, db.ForeignKey("ride_bookings.id", ondelete="CASCADE"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(Enum("Agreed", "Paid", "Refunded", name="contribution_status"), nullable=False, default="Agreed")
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (
        db.CheckConstraint("rating BETWEEN 1 AND 5", name="chk_review_rating"),
        UniqueConstraint("ride_id", "reviewer_id", "reviewed_user_id", name="uq_review_per_ride"),
    )

    id = db.Column(BIGINT, primary_key=True)
    ride_id = db.Column(BIGINT, db.ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    reviewed_user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.SmallInteger, nullable=False)
    comment = db.Column(db.String(1000), nullable=False, default="")
    is_reported = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())

    reviewer = db.relationship("User", foreign_keys=[reviewer_id])
    reviewed_user = db.relationship("User", foreign_keys=[reviewed_user_id])
    ride = db.relationship("Ride")


class Complaint(db.Model):
    __tablename__ = "complaints"
    __table_args__ = (Index("idx_complaint_status", "status", "created_at"),)

    id = db.Column(BIGINT, primary_key=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id", ondelete="SET NULL"))
    contact_email = db.Column(db.String(190), nullable=False)
    kind = db.Column(Enum("Complaint", "User report", "Ride report", "Emergency report", "Support", name="complaint_kind"), nullable=False)
    subject = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(Enum("Open", "Resolved", name="complaint_status"), nullable=False, default="Open")
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    resolved_at = db.Column(db.DateTime)
    user = db.relationship("User")


class EmergencyReport(db.Model):
    __tablename__ = "emergency_reports"

    id = db.Column(BIGINT, primary_key=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id", ondelete="SET NULL"))
    ride_id = db.Column(BIGINT, db.ForeignKey("rides.id", ondelete="SET NULL"))
    details = db.Column(db.Text, nullable=False)
    status = db.Column(Enum("Open", "Reviewed", "Resolved", name="emergency_status"), nullable=False, default="Open")
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    user = db.relationship("User")
    ride = db.relationship("Ride")


class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = (Index("idx_notification_user", "user_id", "is_read", "created_at"),)

    id = db.Column(BIGINT, primary_key=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    user = db.relationship("User")


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("idx_message_booking", "booking_id", "created_at"),)

    id = db.Column(BIGINT, primary_key=True)
    booking_id = db.Column(BIGINT, db.ForeignKey("ride_bookings.id", ondelete="CASCADE"), nullable=False)
    sender_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.String(2000), nullable=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    booking = db.relationship("RideBooking", back_populates="messages")
    sender = db.relationship("User")