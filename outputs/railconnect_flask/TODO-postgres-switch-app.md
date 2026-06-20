# TODO: Switch RailConnect Flask app from SQLite -> PostgreSQL

## Goal
- `outputs/railconnect_flask/app.py` ko PostgreSQL use karna
- Existing endpoints (/, /search, /book, /register, /login, /my-bookings, /cancel, /admin, /api/pnr) same rehn

## Steps
1. Dependencies
   - `requirements.txt` me `psycopg2-binary` add karna
2. Configuration
   - Add env vars (fallback defaults):
     - `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`
   - DB connection function replace karna: `sqlite3.connect` -> `psycopg2.connect`
3. SQL paramstyle conversion
   - Replace `?` placeholders with `%s`
4. SQLite-specific SQL remove
   - `INSERT OR IGNORE` -> `INSERT ... ON CONFLICT DO NOTHING`
   - `INTEGER PRIMARY KEY AUTOINCREMENT` already handled in schema
5. JSON fields
   - Postgres schema uses JSONB for `passengers` and `seats`
   - Code me `json.dumps(...)` ki jagah `json.dumps` ok hai, but ensure psycopg2 gets JSONB
   - Optionally cast: `%s::jsonb`
6. init_db()
   - Seed admin + sample booking implement karna PostgreSQL me
   - `ensure_seat_inventory` ko Postgres me `executemany` ke through
7. Run + verify
   - Start app
   - Register/login + make booking
   - Verify in Postgres DB: rows appear in `users`, `bookings`, `seat_inventory`

