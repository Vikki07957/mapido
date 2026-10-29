# MAPIDO – Smart Ride Sharing

MAPIDO connects drivers travelling to a destination with passengers going the same way. The app is server-rendered with PHP 8+, MySQL/InnoDB, Bootstrap 5 and a small custom responsive stylesheet. MySQL is the source of truth for accounts, rides, bookings, reviews, messages and reports. MongoDB is optional and is not required by this implementation.

## Requirements

- XAMPP with PHP 8.1+ and MySQL/MariaDB enabled
- PHP extensions `pdo_mysql`, `fileinfo` and `mbstring`
- A browser with internet access for the Bootstrap and Google Fonts CDN assets; core layout styles are local

## XAMPP Setup

1. Copy the `mapido` project folder into `C:\xampp\htdocs\mapido` (or use the XAMPP `htdocs` path for your installation).
2. Start Apache and MySQL in the XAMPP Control Panel.
3. Open phpMyAdmin at `http://localhost/phpmyadmin`, import `database/schema.sql`, and confirm the `mapido` database was created.
4. In phpMyAdmin, create an application user for host `localhost` and grant it only `SELECT`, `INSERT`, `UPDATE` and `DELETE` on the `mapido` database. Example SQL (replace the password with your own):

  ```sql
  CREATE USER 'mapido_app'@'localhost' IDENTIFIED BY 'choose-a-local-password';
  GRANT SELECT, INSERT, UPDATE, DELETE ON mapido.* TO 'mapido_app'@'localhost';
  ```

  This does not alter the XAMPP root account or global grants. Copy `config.example.php` to `config.local.php`, then set `db_user` to `mapido_app` and `db_pass` to the password you chose. `config.local.php` is ignored by Git. If that user already exists, update the app config to match its existing credentials rather than recreating the user.
5. Open `http://localhost/mapido/`.
6. To add demo accounts and sample routes, open a command prompt in the project folder and run `C:\xampp\php\php.exe seed.php`.

Import `database/schema.sql` while signed into phpMyAdmin with an account that is allowed to create the database/tables. The separate `mapido_app` user does not need DDL privileges to run the website or seed demo rows.

The demo seeder creates three local-only users. It resets their demo passwords each time it runs. Sample routes are explicitly marked **Sample** and cannot be booked. Publish a regular driver ride to test requests and seat confirmation. The seeded administrator password is only for local demonstration; replace it before any shared deployment.

## Demo Accounts

| Role | Email | Password |
| --- | --- | --- |
| Driver | `driver@mapido.local` | `DriverDemo!2026` |
| Passenger | `passenger@mapido.local` | `RiderDemo!2026` |
| Admin | `admin@mapido.local` | `AdminDemo!2026` |

Public registration cannot create administrator accounts. The CLI demo seeder is the provided local admin bootstrap.

## Main Workflows

- Register and log in as a driver or passenger; passwords use PHP's `password_hash` and `password_verify`, and authenticated forms use CSRF tokens.
- Drivers publish, edit, complete or cancel a ride, add up to eight ordered pickup points, and accept or reject seat requests.
- Passengers search route text and date, request seats, cancel pending or confirmed requests, message eligible ride participants, and review completed journeys.
- Confirmed capacity is checked while the ride row is locked in a MySQL transaction. A driver's ride capacity cannot be edited below confirmed seats.
- Admin users can review reports and reported reviews, suspend or restore non-admin accounts, and resolve complaints. An admin role must be provisioned through database administration or the local demo seeder.
- Profile photos accept JPEG, PNG or WebP up to 2 MB. Phone numbers are not shown in search results.
- OpenStreetMap is linked for route lookup without an API key; location matching is text-based, not a geospatial same-direction algorithm.

## Transparent Limitations

- Cost per seat is an estimate calculated from the driver's entered journey total and published seat capacity. Riders agree the actual amount directly; MAPIDO does not process payments.
- Chat is stored in MySQL and refreshes when a participant opens the conversation. It is not real-time and has no push delivery.
- Emergency reports go to the MAPIDO admin report queue only. This project does not contact emergency services or promise an immediate response.
- The demo does not provide identity verification, user-facing account verification, SMS/email delivery, or map geocoding. “Not verified” is shown unless an administrator changes the database flag.
- Search matches entered origin/destination text and date; it does not compute intermediate-route proximity. Sample rides are demonstration fixtures, not live offers.
- MongoDB is intentionally not connected. If added later, use it only for optional append-only activity or chat data; keep rides and booking state in MySQL and do not make successful bookings depend on MongoDB availability.

## Database and Configuration

`database/schema.sql` contains the relational schema and indexes, including users, vehicles, rides, bookings, pickup points, contributions, reviews, complaints, emergency reports, notifications and chat messages. Local credentials belong in ignored `config.local.php` or environment variables; do not add secrets to public source files. No Google Maps key is needed. The app defaults intentionally point at the dedicated local account shown above, not MySQL root.

## Project Layout

```text
mapido/
  app/                 Shared PHP bootstrap, actions and templates
  assets/              Responsive CSS and progressive-enhancement JS
  database/schema.sql  MySQL schema
  tests/               Manual acceptance test checklist
  config.example.php   Safe local configuration defaults
  index.php            Front controller
  seed.php             CLI-only demo accounts and sample routes
```

## Security Notes

This is an academic demonstration starter, not a production-ready ride marketplace. Deploy behind HTTPS, use a least-privilege MySQL user, set strong secrets, configure upload limits and backups, add rate limiting/email verification, and perform a security review before handling real users or safety incidents. Do not expose the demo credentials publicly.