# MAPIDO – Flask Ride Sharing

MAPIDO connects drivers travelling to a destination with passengers going the same way. The backend is Python 3.12 + Flask, Flask-Login, Flask-WTF, SQLAlchemy and MySQL/MariaDB. The existing CSS and JavaScript were retained under `assets/`; templates are Jinja in `app/templates/`. MongoDB is optional and not used.

## Existing PHP Backup

Before migration, all original project files were copied and verified under `archive/php-legacy/` (26 files). The active PHP backend has been moved to `archive/php-runtime/` after the Flask route tests passed. The original MySQL schema file remains at `database/schema.sql` for reference and for new installations. No existing MySQL data was read, reset, or modified as part of this migration.

## Preserve an Existing Database

The SQLAlchemy models map the existing table names and columns: `users`, `vehicles`, `rides`, `ride_bookings`, `pickup_points`, `payments_or_contributions`, `reviews`, `complaints`, `emergency_reports`, `notifications`, and `chat_messages`. Existing PHP bcrypt password hashes remain login-compatible; successful legacy logins can continue using the stored hash.

For a database that already contains MAPIDO data:

1. Do not re-import the schema, drop tables, call `db.create_all()`, or run the demo seeder against production/student data.
2. Make a backup first from phpMyAdmin Export or, in Command Prompt, `C:\xampp\mysql\bin\mysqldump.exe -u root -p mapido > mapido-backup.sql`. Enter the MySQL password only at the terminal prompt.
3. Compare `database/schema.sql` with the actual database before upgrading. The Flask app performs no schema creation or migration on startup. This migration intentionally introduces no schema changes.
4. Use a MySQL account with database-scoped `SELECT`, `INSERT`, `UPDATE`, and `DELETE` rights. Do not change global privileges or XAMPP root permissions. If an app account already exists, use its existing credentials.
5. Set `DATABASE_URL` in `.env` to that existing database and test reads first. The application must point to the same `mapido` database; do not create a replacement database for a real migration.

The schema file uses `CREATE TABLE IF NOT EXISTS` for fresh installations, not as an upgrade mechanism for an existing database.

## Windows Setup

Requirements: Python 3.12+, XAMPP MySQL/MariaDB, and the packages in `requirements.txt`.

1. Open PowerShell in the project directory (`C:\mapido`).
2. Create a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip --version
   ```

   If PowerShell cannot resolve `python`, use the installed Python executable path, for example `C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv`. Calling `.venv\Scripts\python.exe` directly avoids PowerShell activation-policy changes.
3. Install the dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install --no-binary=SQLAlchemy -r requirements.txt
   ```
4. Copy `.env.example` to `.env`. Set a random `SECRET_KEY` and your existing MySQL connection string. Example only:

   ```dotenv
   SECRET_KEY=put-a-long-random-value-here
   DATABASE_URL=mysql+pymysql://mapido_app:your-password@127.0.0.1:3306/mapido?charset=utf8mb4
   FLASK_DEBUG=0
   SESSION_COOKIE_SECURE=0
   ```

   Create the file with `Copy-Item .env.example .env`, then edit it in VS Code. URL-encode special characters in the username/password part of `DATABASE_URL` (for example `@` becomes `%40`). Keep `.env` private; it is git-ignored. `SESSION_COOKIE_SECURE=0` is for local HTTP only; enable it behind HTTPS in production.
5. Start MySQL in XAMPP. Use the existing database and its existing scoped account. Do not change grants if that account already has the required access. For a fresh database only, import `database/schema.sql` using phpMyAdmin. If you need to create a new local application account, first back up your database and grant only this database (never global privileges):

   ```sql
   CREATE USER 'mapido_app'@'localhost' IDENTIFIED BY 'choose-a-local-password';
   GRANT SELECT, INSERT, UPDATE, DELETE ON mapido.* TO 'mapido_app'@'localhost';
   ```

   The account does not need schema/DDL privileges. Do not run `CREATE USER` if it already exists; use its existing credentials.
6. Start Flask:

   ```powershell
   .\.venv\Scripts\python.exe -m flask --app run.py run --host 127.0.0.1 --port 5000
   ```

   Or run `.\.venv\Scripts\python.exe run.py`. Open **http://127.0.0.1:5000/**. Apache is not required for the Flask application.
7. Optional: seed local demo accounts/sample routes only in a disposable development database:

   ```powershell
   .\.venv\Scripts\python.exe seed_demo.py
   ```

   The seeder updates its three demo accounts and sample rides, resetting demo passwords each time. Never run it against a database containing real MAPIDO users or rides.

Flask-WTF protects POST routes with CSRF tokens. Session cookies are HTTP-only and SameSite=Lax; HTTPS deployments should set secure cookies. Passwords created by Flask use scrypt; PHP bcrypt hashes are supported for backward-compatible login.

## Demo Accounts

Only after explicitly seeding a development database:

| Role | Email | Password |
| --- | --- | --- |
| Driver | `driver@mapido.local` | `DriverDemo!2026` |
| Passenger | `passenger@mapido.local` | `RiderDemo!2026` |
| Admin | `admin@mapido.local` | `AdminDemo!2026` |

Seeded routes are marked **Sample** and cannot be booked, including by forged POST requests.

## Routes and Features

- `/` landing page; `/auth/register`, `/auth/login`, `/auth/logout`
- `/rides` route/date/time/seat/contribution search; `/rides/offer` ride publication
- Driver ride edit/cancel/complete and passenger booking/cancellation/review routes
- `/dashboard`, `/bookings`, `/chat/`, `/profile/`, `/support/`, `/admin/`
- MySQL transactions lock the ride row when booking seats are requested/confirmed or capacity is edited. A database unique key prevents duplicate active bookings. Confirmation checks current confirmed seats while holding the ride lock.
- Uploads are limited to JPEG, PNG or WebP images and 2 MB. Private phone numbers are not shown in search results.
- Estimated contributions are not payments. Chat is basic database messaging, not real-time. Emergency reports go to the MAPIDO admin queue and do not contact emergency services.
- Search is text/date based, not geospatial same-direction matching. OpenStreetMap links require no API key.

## Tests and Verification

Run isolated route/service tests with SQLite (they do not touch MySQL):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover account registration/login, protected access, role validation, ride publication/search, active-booking duplicate prevention, seat overbooking, cancellation, profile/password changes, completed-ride reviews, admin access, reports, sample-ride restrictions, and PHP bcrypt compatibility. In this Windows environment SQLAlchemy's optional native extension was blocked by Application Control, so dependencies were installed with `--no-binary=SQLAlchemy`; keep that option if you see a blocked-DLL import error. MySQL concurrency depends on InnoDB row locks and should also be exercised against a dedicated disposable MySQL database before deployment.

Do not use `db.create_all()` with a populated database. Flask-Migrate is installed for future explicit migrations, but this migration has no migration scripts because it does not alter the schema.

## Production Note

Do not use Flask's development server or debug mode in production. Use a production WSGI server behind HTTPS, strong secret management, least-privilege database credentials, secure cookie settings, backups, rate limiting and a security review. MongoDB is intentionally not connected; MySQL remains the source of truth for all ride and booking records.
