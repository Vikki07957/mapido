from datetime import date, time, timedelta

from sqlalchemy import func, select

from app.extensions import db
from app.models import ChatMessage, Complaint, EmergencyReport, Review, Ride, RideBooking, User, Vehicle
from app.services.bookings import request_seats, update_booking_status
from seed_demo import seed_demo


def create_user(email, role, name=None):
    user = User(name=name or email.split("@")[0], email=email, role=role)
    user.set_password("MapidoTest!2026")
    db.session.add(user)
    db.session.flush()
    db.session.commit()
    return user


def create_ride(driver, seats=2):
    vehicle = Vehicle(user_id=driver.id, model="Test car", registration_number="TEST 123")
    db.session.add(vehicle)
    db.session.flush()
    ride = Ride(driver_id=driver.id, vehicle_id=vehicle.id, origin="Sullia", destination="Mangaluru", travel_date=date.today() + timedelta(days=2), departure_time=time(9), total_seats=seats, estimated_cost=600)
    db.session.add(ride)
    db.session.commit()
    return ride


def test_registration_login_logout_and_protected_page(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    response = client.post("/auth/register", data={"name": "Rider One", "email": "rider@example.com", "phone": "", "role": "passenger", "password": "MapidoTest!2026"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Good day, Rider" in response.data
    client.post("/auth/logout")
    response = client.post("/auth/login", data={"email": "rider@example.com", "password": "MapidoTest!2026"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Good day, Rider" in response.data
    client.post("/auth/logout")
    assert client.get("/dashboard").status_code == 302


def test_registration_rejects_admin_role_and_short_password(client):
    response = client.post("/auth/register", data={"name": "Bad", "email": "bad@example.com", "role": "admin", "password": "short"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Create your account" in response.data
    with client.application.app_context():
        assert db.session.scalar(select(User.id).where(User.email == "bad@example.com")) is None


def test_ride_offer_search_and_sample_routes_not_bookable(client):
    client.post("/auth/register", data={"name": "Driver One", "email": "driver@example.com", "role": "driver", "password": "MapidoTest!2026"})
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = client.post("/rides/offer", data={"origin": "Sullia", "destination": "Mangaluru", "travel_date": tomorrow, "departure_time": "09:30", "seats": 2, "vehicle": "Test car", "registration": "TEST 001", "estimated_cost": "600", "notes": "", "pickup_points": "Bantwal"}, follow_redirects=True)
    assert response.status_code == 200
    response = client.get("/rides?origin=Sullia&destination=Mangaluru&date=" + tomorrow)
    assert b"Sullia" in response.data and b"Mangaluru" in response.data
    assert b"Bantwal" in response.data


def test_seat_confirmation_prevents_overbooking(client, app):
    with app.app_context():
        driver = create_user("driver1@example.com", "driver")
        passenger_one = create_user("passenger1@example.com", "passenger")
        passenger_two = create_user("passenger2@example.com", "passenger")
        ride = create_ride(driver, seats=1)
        first = request_seats(ride.id, passenger_one, 1)
        second = request_seats(ride.id, passenger_two, 1)
        update_booking_status(first.id, driver, "Confirmed")
        try:
            update_booking_status(second.id, driver, "Confirmed")
        except ValueError as error:
            assert "Not enough seats" in str(error)
        else:
            raise AssertionError("The second confirmation must not overbook the ride.")
        assert db.session.get(RideBooking, first.id).status == "Confirmed"
        assert db.session.get(RideBooking, second.id).status == "Pending"


def test_duplicate_active_booking_is_rejected(app):
    with app.app_context():
        driver = create_user("driver2@example.com", "driver")
        passenger = create_user("passenger3@example.com", "passenger")
        ride = create_ride(driver, seats=2)
        request_seats(ride.id, passenger, 1)
        try:
            request_seats(ride.id, passenger, 1)
        except ValueError as error:
            assert "active request" in str(error)
        else:
            raise AssertionError("Duplicate active booking was accepted.")


def test_sample_rides_cannot_be_booked(app):
    with app.app_context():
        driver = create_user("sample-driver@example.com", "driver")
        passenger = create_user("sample-passenger@example.com", "passenger")
        ride = create_ride(driver, seats=2)
        ride.is_sample = True
        db.session.commit()
        try:
            request_seats(ride.id, passenger, 1)
        except ValueError as error:
            assert "no longer available" in str(error)
        else:
            raise AssertionError("Sample rides must never be bookable.")


def test_legacy_php_bcrypt_hash_is_accepted(app):
    legacy_hash = "$2y$10$iubD6xZ4u2Q.i8/1Mv7gH.WTL9OG3fRDLjPdrKjiLfQmHwNX.nwcW"
    with app.app_context():
        user = User(name="Legacy User", email="legacy@example.com", role="passenger", password_hash=legacy_hash)
        assert user.check_password("LegacyMapido!2026")
        assert not user.check_password("wrong-password")


def test_booking_cancellation_releases_confirmed_seats(client, app):
    with app.app_context():
        driver = create_user("cancel-driver@example.com", "driver")
        passenger = create_user("cancel-passenger@example.com", "passenger")
        ride = create_ride(driver, seats=1)
        booking = request_seats(ride.id, passenger, 1)
        booking.status = "Confirmed"
        db.session.commit()
        booking_id = booking.id
        passenger_id = passenger.id
        ride_id = ride.id
    with client.session_transaction() as session:
        session["_user_id"] = str(passenger_id)
        session["_fresh"] = True
    response = client.post(f"/rides/bookings/{booking_id}/cancel", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(RideBooking, booking_id).status == "Cancelled"
        assert db.session.scalar(select(RideBooking.id).where(RideBooking.ride_id == ride_id, RideBooking.status == "Confirmed")) is None


def test_profile_update_and_password_change(client, app):
    with app.app_context():
        user = create_user("profile@example.com", "passenger", "Profile User")
        user_id = user.id
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    response = client.post("/profile/", data={"save_profile": "1", "name": "Updated Name", "phone": "12345"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.name == "Updated Name"
        assert user.phone == "12345"
    response = client.post("/profile/", data={"change_password": "1", "current_password": "MapidoTest!2026", "new_password": "ChangedTest!2026"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(User, user_id).check_password("ChangedTest!2026")


def test_completed_booking_review_and_duplicate_guard(client, app):
    with app.app_context():
        driver = create_user("review-driver@example.com", "driver")
        passenger = create_user("review-passenger@example.com", "passenger")
        ride = create_ride(driver, seats=1)
        ride.travel_date = date.today() - timedelta(days=1)
        ride.status = "Completed"
        booking = RideBooking(ride=ride, passenger_id=passenger.id, seats=1, status="Completed")
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id
        ride_id = ride.id
        passenger_id = passenger.id
    client.post("/auth/login", data={"email": "review-passenger@example.com", "password": "MapidoTest!2026"})
    response = client.post(f"/rides/bookings/{booking_id}/review", data={"rating": "5", "comment": "Great trip"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        review = db.session.scalar(select(Review).where(Review.ride_id == ride_id, Review.reviewer_id == passenger_id))
        assert review is not None and review.rating == 5
        db.session.expunge_all()
    response = client.post(f"/rides/bookings/{booking_id}/review", data={"rating": "4", "comment": "Duplicate"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(select(func.count(Review.id)).where(Review.ride_id == ride_id, Review.reviewer_id == passenger_id)) == 1


def test_admin_permissions_and_emergency_report(client, app):
    with app.app_context():
        passenger = create_user("ordinary@example.com", "passenger")
        admin = create_user("admin@example.com", "admin")
        passenger_id, admin_id = passenger.id, admin.id
    with client.session_transaction() as session:
        session["_user_id"] = str(passenger_id)
        session["_fresh"] = True
    assert client.get("/admin/").status_code == 403
    client.post("/auth/logout")
    client.post("/auth/login", data={"email": "admin@example.com", "password": "MapidoTest!2026"})
    assert client.get("/admin/").status_code == 200
    client.post("/auth/logout")
    response = client.post("/support/", data={"email": "guest@example.com", "kind": "Emergency report", "subject": "Need help", "body": "Test report"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(select(func.count(Complaint.id))) == 1
        assert db.session.scalar(select(func.count(EmergencyReport.id))) == 1


def test_chat_requires_confirmed_ride_participation(client, app):
    with app.app_context():
        driver = create_user("chat-driver@example.com", "driver")
        passenger = create_user("chat-passenger@example.com", "passenger")
        outsider = create_user("chat-outsider@example.com", "passenger")
        ride = create_ride(driver, seats=1)
        ride.travel_date = date.today()
        booking = RideBooking(ride=ride, passenger_id=passenger.id, seats=1, status="Confirmed")
        db.session.add(booking)
        db.session.commit()
        booking_id, passenger_id = booking.id, passenger.id
    client.post("/auth/login", data={"email": "chat-passenger@example.com", "password": "MapidoTest!2026"})
    response = client.get(f"/chat/{booking_id}")
    assert response.status_code == 200
    response = client.post(f"/chat/{booking_id}", data={"body": "I will meet at the station."}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        message = db.session.scalar(select(ChatMessage).where(ChatMessage.booking_id == booking_id))
        assert message and message.body == "I will meet at the station."
        outsider_id = db.session.scalar(select(User.id).where(User.email == "chat-outsider@example.com"))
    client.post("/auth/logout")
    with client.session_transaction() as session:
        session["_user_id"] = str(outsider_id)
        session["_fresh"] = True
    assert client.get(f"/chat/{booking_id}").status_code == 302


def test_upload_route_rejects_non_image_files(client):
    response = client.get("/uploads/payload.php")
    assert response.status_code == 404


def test_demo_seeder_is_idempotent(app):
    seed_demo(app)
    seed_demo(app)
    with app.app_context():
        assert db.session.scalar(select(func.count(User.id))) == 3
        assert db.session.scalar(select(func.count(Vehicle.id))) == 1
        assert db.session.scalar(select(func.count(Ride.id)).where(Ride.is_sample.is_(True))) == 3