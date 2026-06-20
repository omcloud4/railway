-- RailConnect PostgreSQL schema (derived from app.py SQLite schema)
-- Note: app.py stores passengers/seats as JSON strings; in Postgres you can keep them as TEXT or JSONB.
-- This schema uses JSONB for stronger typing.

BEGIN;

-- USERS
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  mobile TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  created_at TIMESTAMPTZ NOT NULL
);

-- BOOKINGS
CREATE TABLE IF NOT EXISTS bookings (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT,
  pnr TEXT NOT NULL UNIQUE,
  train_id TEXT NOT NULL,
  train_name TEXT NOT NULL,
  route TEXT NOT NULL,
  journey_date TEXT NOT NULL,
  class_key TEXT NOT NULL,
  passengers JSONB NOT NULL,
  seats JSONB NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,

  CONSTRAINT bookings_user_fk
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE SET NULL
);

-- Seat inventory is per train+journey_date+class.
-- confirmed_remaining means currently available confirmed seats.
CREATE TABLE IF NOT EXISTS seat_inventory (
  id BIGSERIAL PRIMARY KEY,
  train_id TEXT NOT NULL,
  journey_date TEXT NOT NULL,
  class_key TEXT NOT NULL,
  confirmed_remaining INTEGER NOT NULL,
  waitlist_capacity INTEGER NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,

  CONSTRAINT seat_inventory_unique
    UNIQUE (train_id, journey_date, class_key)
);

-- Helpful indexes for common queries in app.py
CREATE INDEX IF NOT EXISTS idx_bookings_user_id_created_at ON bookings(user_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_bookings_train_date_status ON bookings(train_id, journey_date, status);
CREATE INDEX IF NOT EXISTS idx_bookings_train_date_class_status ON bookings(train_id, journey_date, class_key, status);
CREATE INDEX IF NOT EXISTS idx_seat_inventory_train_date ON seat_inventory(train_id, journey_date);

COMMIT;

