from datetime import date, timedelta

from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()

from app import create_app
from app.extensions import db
from app.models import Ride, User, Vehicle

DEMO_USERS = [
    ("MAPIDO Demo Driver", "driver@mapido.local", "DriverDemo!2026", "driver"),
    ("MAPIDO Demo Passenger", "passenger@mapido.local", "RiderDemo!2026", "passenger"),
    ("MAPIDO Demo Admin", "admin@mapido.local", "AdminDemo!2026", "admin"),
]
DEMO_ROUTES = [
    ("Sullia", "Mangaluru", 1, "08:15", 600),
    ("Mangaluru", "Puttur", 3, "09:00", 400),
    ("Puttur", "Bengaluru", 7, "21:30", 1800),
]


def seed_demo(app=None):
    app = app or create_app()
    with app.app_context():
        users = {}
        for name, email, password, role in DEMO_USERS:
            user = db.session.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(name=name, email=email, role=role)
                db.session.add(user)
            user.name = name
            user.role = role
            user.is_suspended = False
            user.set_password(password)
            users[role] = user
        db.session.flush()

        driver = users["driver"]
        vehicle = db.session.scalar(select(Vehicle).where(Vehicle.user_id == driver.id))
        if vehicle is None:
            vehicle = Vehicle(user_id=driver.id, model="Demo hatchback", registration_number="KA 19 DZ 2046")
            db.session.add(vehicle)
            db.session.flush()
        vehicle.model = "Demo hatchback"
        vehicle.registration_number = "KA 19 DZ 2046"

        for origin, destination, offset, depart, cost in DEMO_ROUTES:
            ride = db.session.scalar(select(Ride).where(
                Ride.driver_id == driver.id,
                Ride.origin == origin,
                Ride.destination == destination,
                Ride.is_sample.is_(True),
            ))
            travel_date = date.today() + timedelta(days=offset)
            if ride is None:
                ride = Ride(driver_id=driver.id, origin=origin, destination=destination, is_sample=True)
                db.session.add(ride)
            ride.vehicle_id = vehicle.id
            ride.travel_date = travel_date
            from datetime import time
            ride.departure_time = time.fromisoformat(depart)
            ride.total_seats = 3
            ride.estimated_cost = cost
            ride.notes = "Demonstration route. Sample data only."
            ride.status = "Open"
        db.session.commit()
        print("Demo accounts refreshed and sample routes are ready.")
        for _, email, password, role in DEMO_USERS:
            print(f"{role.title()}: {email} / {password}")
        print("Sample listings cannot be booked; publish a non-sample ride to test booking.")


if __name__ == "__main__":
    seed_demo()