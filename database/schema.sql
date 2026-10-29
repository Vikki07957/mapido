CREATE DATABASE IF NOT EXISTS mapido CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mapido;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(190) NOT NULL UNIQUE,
  phone VARCHAR(30) NULL,
  profile_photo VARCHAR(255) NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('driver','passenger','admin') NOT NULL DEFAULT 'passenger',
  is_verified TINYINT(1) NOT NULL DEFAULT 0,
  is_suspended TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_users_role (role,is_suspended)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS vehicles (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL UNIQUE,
  model VARCHAR(100) NOT NULL,
  registration_number VARCHAR(20) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_vehicle_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rides (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  driver_id BIGINT UNSIGNED NOT NULL,
  vehicle_id BIGINT UNSIGNED NULL,
  origin VARCHAR(100) NOT NULL,
  destination VARCHAR(100) NOT NULL,
  travel_date DATE NOT NULL,
  departure_time TIME NOT NULL,
  total_seats TINYINT UNSIGNED NOT NULL,
  estimated_cost DECIMAL(10,2) NOT NULL DEFAULT 0,
  notes VARCHAR(1000) NULL,
  status ENUM('Open','Completed','Cancelled') NOT NULL DEFAULT 'Open',
  is_sample TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ride_driver FOREIGN KEY (driver_id) REFERENCES users(id),
  CONSTRAINT fk_ride_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL,
  CONSTRAINT chk_ride_seats CHECK (total_seats BETWEEN 1 AND 8),
  CONSTRAINT chk_ride_cost CHECK (estimated_cost >= 0),
  INDEX idx_ride_search (status,travel_date,origin,destination)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ride_bookings (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ride_id BIGINT UNSIGNED NOT NULL,
  passenger_id BIGINT UNSIGNED NOT NULL,
  seats TINYINT UNSIGNED NOT NULL DEFAULT 1,
  status ENUM('Pending','Confirmed','Rejected','Completed','Cancelled') NOT NULL DEFAULT 'Pending',
  active_passenger_id BIGINT UNSIGNED GENERATED ALWAYS AS (CASE WHEN status IN ('Pending','Confirmed') THEN passenger_id ELSE NULL END) STORED,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_booking_ride FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE,
  CONSTRAINT fk_booking_passenger FOREIGN KEY (passenger_id) REFERENCES users(id),
  CONSTRAINT chk_booking_seats CHECK (seats BETWEEN 1 AND 8),
  INDEX idx_booking_ride_status (ride_id,status),
  INDEX idx_booking_passenger (passenger_id,status),
  UNIQUE KEY uq_active_booking (ride_id,active_passenger_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pickup_points (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ride_id BIGINT UNSIGNED NOT NULL,
  label VARCHAR(120) NOT NULL,
  sequence_no SMALLINT UNSIGNED NOT NULL,
  CONSTRAINT fk_pickup_ride FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE,
  UNIQUE KEY uq_pickup_sequence (ride_id,sequence_no)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS payments_or_contributions (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  booking_id BIGINT UNSIGNED NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  status ENUM('Agreed','Paid','Refunded') NOT NULL DEFAULT 'Agreed',
  note VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_contribution_booking FOREIGN KEY (booking_id) REFERENCES ride_bookings(id) ON DELETE CASCADE,
  CONSTRAINT chk_contribution_amount CHECK (amount >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reviews (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ride_id BIGINT UNSIGNED NOT NULL,
  reviewer_id BIGINT UNSIGNED NOT NULL,
  reviewed_user_id BIGINT UNSIGNED NOT NULL,
  rating TINYINT UNSIGNED NOT NULL,
  comment VARCHAR(1000) NOT NULL DEFAULT '',
  is_reported TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_review_ride FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE,
  CONSTRAINT fk_review_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id),
  CONSTRAINT fk_review_target FOREIGN KEY (reviewed_user_id) REFERENCES users(id),
  CONSTRAINT chk_review_rating CHECK (rating BETWEEN 1 AND 5),
  UNIQUE KEY uq_review_per_ride (ride_id,reviewer_id,reviewed_user_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS complaints (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NULL,
  contact_email VARCHAR(190) NOT NULL,
  kind ENUM('Complaint','User report','Ride report','Emergency report','Support') NOT NULL,
  subject VARCHAR(160) NOT NULL,
  body TEXT NOT NULL,
  status ENUM('Open','Resolved') NOT NULL DEFAULT 'Open',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at TIMESTAMP NULL,
  CONSTRAINT fk_complaint_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_complaint_status (status,created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS emergency_reports (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NULL,
  ride_id BIGINT UNSIGNED NULL,
  details TEXT NOT NULL,
  status ENUM('Open','Reviewed','Resolved') NOT NULL DEFAULT 'Open',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_emergency_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT fk_emergency_ride FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,
  message VARCHAR(255) NOT NULL,
  is_read TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_notification_user (user_id,is_read,created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS chat_messages (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  booking_id BIGINT UNSIGNED NOT NULL,
  sender_id BIGINT UNSIGNED NOT NULL,
  body VARCHAR(2000) NOT NULL,
  read_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_message_booking FOREIGN KEY (booking_id) REFERENCES ride_bookings(id) ON DELETE CASCADE,
  CONSTRAINT fk_message_sender FOREIGN KEY (sender_id) REFERENCES users(id),
  INDEX idx_message_booking (booking_id,created_at)
) ENGINE=InnoDB;