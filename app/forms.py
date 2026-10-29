from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import DateField, DecimalField, IntegerField, PasswordField, SelectField, StringField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=190)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    role = SelectField("I’m joining as", choices=[("passenger", "Passenger"), ("driver", "Driver")], validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=10, max=128)])


class LoginForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=190)])
    password = PasswordField("Password", validators=[DataRequired()])


class RideForm(FlaskForm):
    origin = StringField("Starting location", validators=[DataRequired(), Length(max=100)])
    destination = StringField("Destination", validators=[DataRequired(), Length(max=100)])
    travel_date = DateField("Travel date", validators=[DataRequired()], format="%Y-%m-%d")
    departure_time = TimeField("Departure time", validators=[DataRequired()], format="%H:%M")
    seats = IntegerField("Available seats", validators=[DataRequired(), NumberRange(min=1, max=8)])
    vehicle = StringField("Vehicle model", validators=[DataRequired(), Length(max=100)])
    registration = StringField("Registration number", validators=[DataRequired(), Length(max=20)])
    estimated_cost = DecimalField("Estimated total journey cost (₹)", validators=[DataRequired(), NumberRange(min=0, max=100000)], places=2)
    notes = StringField("Travel notes", validators=[Optional(), Length(max=1000)])
    pickup_points = TextAreaField("Pickup points", validators=[Optional(), Length(max=600)])


class RideEditForm(FlaskForm):
    origin = StringField("Origin", validators=[DataRequired(), Length(max=100)])
    destination = StringField("Destination", validators=[DataRequired(), Length(max=100)])
    travel_date = DateField("Date", validators=[DataRequired()], format="%Y-%m-%d")
    departure_time = TimeField("Departure", validators=[DataRequired()], format="%H:%M")
    seats = IntegerField("Total seats", validators=[DataRequired(), NumberRange(min=1, max=8)])
    estimated_cost = DecimalField("Estimated journey cost", validators=[DataRequired(), NumberRange(min=0, max=100000)], places=2)
    notes = StringField("Travel notes", validators=[Optional(), Length(max=1000)])
    pickup_points = TextAreaField("Pickup points", validators=[Optional(), Length(max=600)])


class ProfileForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    profile_photo = FileField("Profile photo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Upload a JPEG, PNG or WebP image.")])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=10, max=128)])


class SupportForm(FlaskForm):
    email = StringField("Your email", validators=[Optional(), Email(), Length(max=190)])
    kind = SelectField("What is this about?", choices=[("Support", "Support"), ("Complaint", "Complaint"), ("User report", "User report"), ("Ride report", "Ride report"), ("Emergency report", "Emergency report")], validators=[DataRequired()])
    subject = StringField("Subject", validators=[DataRequired(), Length(max=160)])
    body = TextAreaField("Details", validators=[DataRequired(), Length(max=3000)])


class MessageForm(FlaskForm):
    body = StringField("Message", validators=[DataRequired(), Length(max=2000)])


class ReviewForm(FlaskForm):
    rating = SelectField("Rating", choices=[(str(n), f"{n} - {label}") for n, label in [(5, "Excellent"), (4, "Good"), (3, "Okay"), (2, "Poor"), (1, "Very poor")]], coerce=int, validators=[DataRequired()])
    comment = TextAreaField("Feedback", validators=[Optional(), Length(max=1000)])


class BookingSeatsForm(FlaskForm):
    seats = IntegerField("Seats", validators=[DataRequired(), NumberRange(min=1, max=8)])