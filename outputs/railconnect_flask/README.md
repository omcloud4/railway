# RailConnect Flask

IRCTC-style railway booking portal converted from the provided React concept into a Flask + SQLite app.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

The app creates `railconnect.db` automatically on first run.

Pages:

- Home/search: `http://127.0.0.1:5000/`
- Register: `http://127.0.0.1:5000/register`
- Login: `http://127.0.0.1:5000/login`
- My Bookings: `http://127.0.0.1:5000/my-bookings`
- Admin: `http://127.0.0.1:5000/admin`

## Demo Accounts

- Admin: `admin@railconnect.test` / `admin123`
- User: register from the top bar, then login with that account.

## Included

- Register and login with hashed passwords
- SQLite users and bookings database
- Train search and class availability
- Passenger details and payment method form
- PNR generation and e-ticket page
- My Bookings page with cancellation
- Admin dashboard with users, bookings, trains, and revenue
