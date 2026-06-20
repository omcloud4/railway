import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from random import randint

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = "railconnect-demo-secret"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "railconnect.db"


TRAINS = [
    {
        "id": "12301",
        "name": "Rajdhani Express",
        "from": "NDLS",
        "from_name": "New Delhi",
        "to": "HWH",
        "to_name": "Howrah",
        "dep": "16:55",
        "arr": "10:00",
        "duration": "17h 05m",
        "days": "Mon Tue Wed Thu Fri Sat Sun",
        "classes": {"SL": [715, 42], "3A": [1885, 18], "2A": [2760, 6], "1A": [4580, 2]},
        "type": "Rajdhani",
        "distance": 1447,
    },
    {
        "id": "12302",
        "name": "Shatabdi Express",
        "from": "NDLS",
        "from_name": "New Delhi",
        "to": "CDG",
        "to_name": "Chandigarh",
        "dep": "07:20",
        "arr": "10:40",
        "duration": "3h 20m",
        "days": "Mon Tue Wed Thu Fri Sat",
        "classes": {"CC": [720, 85], "EC": [1380, 20]},
        "type": "Shatabdi",
        "distance": 248,
    },
    {
        "id": "22435",
        "name": "Vande Bharat Express",
        "from": "NDLS",
        "from_name": "New Delhi",
        "to": "KOTA",
        "to_name": "Kota Jn",
        "dep": "06:00",
        "arr": "13:45",
        "duration": "7h 45m",
        "days": "Mon Tue Wed Thu Fri Sat Sun",
        "classes": {"CC": [1200, 112], "EC": [2200, 30]},
        "type": "Vande Bharat",
        "distance": 456,
    },
    {
        "id": "12951",
        "name": "Mumbai Rajdhani",
        "from": "NDLS",
        "from_name": "New Delhi",
        "to": "MMCT",
        "to_name": "Mumbai Central",
        "dep": "16:00",
        "arr": "08:35",
        "duration": "16h 35m",
        "days": "Mon Wed Fri",
        "classes": {"SL": [850, 0], "3A": [2220, 4], "2A": [3270, 8], "1A": [5480, 1]},
        "type": "Rajdhani",
        "distance": 1384,
    },
    {
        "id": "12565",
        "name": "Bihar Sampark Kranti",
        "from": "NDLS",
        "from_name": "New Delhi",
        "to": "PNBE",
        "to_name": "Patna Jn",
        "dep": "14:15",
        "arr": "05:45",
        "duration": "15h 30m",
        "days": "Tue Thu Sat",
        "classes": {"SL": [560, 120], "3A": [1475, 35], "2A": [2145, 12]},
        "type": "Express",
        "distance": 1001,
    },
    {
        "id": "12649",
        "name": "Karnataka Sampark Kranti",
        "from": "NDLS",
        "from_name": "New Delhi",
        "to": "YPR",
        "to_name": "Yeshwantpur",
        "dep": "21:30",
        "arr": "06:00",
        "duration": "32h 30m",
        "days": "Mon Fri",
        "classes": {"SL": [1045, 65], "3A": [2755, 22], "2A": [4025, 8]},
        "type": "Express",
        "distance": 2367,
    },
]

STATIONS = [
    "NDLS - New Delhi",
    "HWH - Howrah",
    "MMCT - Mumbai Central",
    "MAS - Chennai Central",
    "SBC - Bangalore City",
    "PNBE - Patna Jn",
    "CDG - Chandigarh",
    "KOTA - Kota Jn",
    "YPR - Yeshwantpur",
    "ADI - Ahmedabad",
    "LKO - Lucknow",
    "BPL - Bhopal",
]

CLASS_NAMES = {
    "SL": "Sleeper",
    "3A": "AC 3 Tier",
    "2A": "AC 2 Tier",
    "1A": "AC First Class",
    "CC": "Chair Car",
    "EC": "Executive Chair",
}


def station_code(value):
    query = (value or "").strip()
    if not query:
        return ""
    normalized = query.upper()
    if " - " in normalized:
        return normalized.split(" - ")[0].strip()
    for station in STATIONS:
        code, name = station.split(" - ", 1)
        if normalized == code.upper() or normalized == name.upper() or normalized in station.upper():
            return code
    return normalized


def station_label(code):
    for station in STATIONS:
        station_code_value, name = station.split(" - ", 1)
        if station_code_value == code:
            return f"{code} - {name}"
    return code


def find_train(train_id):
    return next((train for train in TRAINS if train["id"] == train_id), None)


def waitlist_capacity_for_confirmed(confirmed):
    # waitlist capacity = ceil(confirmed * 0.5), minimum 1 when confirmed > 0
    if confirmed <= 0:
        return 0
    return max(1, int((confirmed * 0.5) + 0.999999))


def ensure_seat_inventory(connection):
    """Seed seat inventory for all trains/classes across near-future dates.

    The UI reads confirmed_remaining from seat_inventory for the selected journey_date.
    Previously we seeded only for journey_date values already present in `bookings`,
    which caused many search dates to show 0 availability ("SOLD OUT").

    This demo now seeds a small date horizon so availability works for typical searches.
    """

    # Seed today..today+14
    horizon_days = 14
    journey_dates = [(date.today() + timedelta(days=i)).isoformat() for i in range(horizon_days + 1)]


    rows_to_insert = []
    for t in TRAINS:
        for class_key, (fare, confirmed) in t["classes"].items():
            wc = waitlist_capacity_for_confirmed(confirmed)
            for d in journey_dates:
                rows_to_insert.append(
                    (
                        t["id"],
                        d,
                        class_key,
                        confirmed,
                        wc,
                        datetime.now().isoformat(timespec="seconds"),
                    )
                )


    connection.executemany(
        """
        INSERT OR IGNORE INTO seat_inventory
        (train_id, journey_date, class_key, confirmed_remaining, waitlist_capacity, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows_to_insert,
    )



def price_for(train, class_key, passengers):
    fare = train["classes"][class_key][0]
    base = fare * passengers
    tax = round(base * 0.05)
    convenience = 35
    return {"base": base, "tax": tax, "convenience": convenience, "total": base + tax + convenience}


def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            mobile TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            pnr TEXT NOT NULL UNIQUE,
            train_id TEXT NOT NULL,
            train_name TEXT NOT NULL,
            route TEXT NOT NULL,
            journey_date TEXT NOT NULL,
            class_key TEXT NOT NULL,
            passengers TEXT NOT NULL,
            seats TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        -- Seat inventory is per train+journey_date+class.
        -- confirmed_remaining means currently available confirmed seats.
        CREATE TABLE IF NOT EXISTS seat_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id TEXT NOT NULL,
            journey_date TEXT NOT NULL,
            class_key TEXT NOT NULL,
            confirmed_remaining INTEGER NOT NULL,
            waitlist_capacity INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(train_id, journey_date, class_key)
        );
        """
    )
    admin = connection.execute("SELECT id FROM users WHERE email = ?", ("admin@railconnect.test",)).fetchone()
    if not admin:
        cursor = connection.execute(
            """
            INSERT INTO users (name, email, mobile, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "RailConnect Admin",
                "admin@railconnect.test",
                "9999999999",
                generate_password_hash("admin123"),
                "admin",
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        admin_id = cursor.lastrowid
    else:
        admin_id = admin["id"]

    existing_booking = connection.execute("SELECT id FROM bookings WHERE pnr = ?", ("PNR5628139042",)).fetchone()
    if not existing_booking:
        connection.execute(
            """
            INSERT INTO bookings
            (user_id, pnr, train_id, train_name, route, journey_date, class_key, passengers, seats, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                admin_id,
                "PNR5628139042",
                "12301",
                "Rajdhani Express",
                "New Delhi to Howrah",
                "2026-06-18",
                "3A",
                json.dumps(["Rahul Sharma", "Priya Sharma"]),
                json.dumps(["B1-21", "B1-22"]),
                4050,
                "confirmed",
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
    # Seed seat inventory after schema is ready (if needed).
    ensure_seat_inventory(connection)
    connection.commit()
    connection.close()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    connection = db()
    user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    connection.close()
    return dict(user) if user else None


def row_to_booking(row):
    return {
        "pnr": row["pnr"],
        "train": row["train_name"],
        "route": row["route"],
        "date": row["journey_date"],
        "class": row["class_key"],
        "passengers": json.loads(row["passengers"]),
        "amount": row["amount"],
        "status": row["status"],
        "seats": json.loads(row["seats"]),
    }


def recent_bookings(user_id=None, limit=3):
    connection = db()
    if user_id:
        rows = connection.execute(
            "SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    else:
        rows = connection.execute("SELECT * FROM bookings ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    connection.close()
    return [row_to_booking(row) for row in rows]


def availability_for_selection(connection, train_id: str, journey_date: str):
    """Return per class inventory + waitlisted count estimate for UI.

    UI requirement for college demo: show Available / RAC(approx) / WL.
    We currently track only confirmed_remaining precisely.
    WL is derived from waitlisted bookings count (for that class/date/train).

    RAC is approximated as 0 (or could be added later with another column).
    """
    inv_rows = connection.execute(
        """
        SELECT class_key, confirmed_remaining
        FROM seat_inventory
        WHERE train_id = ? AND journey_date = ?
        """,
        (train_id, journey_date),
    ).fetchall()

    inv_map = {r["class_key"]: int(r["confirmed_remaining"]) for r in inv_rows}

    wl_rows = connection.execute(
        """
        SELECT class_key, COUNT(*) AS cnt
        FROM bookings
        WHERE train_id = ? AND journey_date = ? AND status = 'waitlisted'
        GROUP BY class_key
        """,
        (train_id, journey_date),
    ).fetchall()
    wl_map = {}
    for r in wl_rows:
        wl_map[r["class_key"]] = int(r["cnt"])

    # Convert to UI-ready dict with labels expected by templates.
    out = {}
    for class_key in CLASS_NAMES.keys():
        confirmed = inv_map.get(class_key, 0)
        wl_count = wl_map.get(class_key, 0)
        out[class_key] = {"confirmed": confirmed, "wl_bookings": wl_count}
    return out


@app.route("/")
def index():

    user = current_user()
    if not user:
        return redirect(url_for("register"))
    today = date.today().isoformat()
    connection = db()
    inventory = {}
    for t in TRAINS:
        key = f"{t['id']}:{today}"
        inv = availability_for_selection(connection, t['id'], today)
        inventory[key] = inv
    connection.close()

    return render_template(
        "index.html",
        trains=TRAINS,
        stations=STATIONS,
        class_names=CLASS_NAMES,
        today=today,
        bookings=recent_bookings(user["id"] if user else None),
        user=user,
        display_trains=TRAINS,
        inventory=inventory,
    )




@app.post("/search")
def search():
    user = current_user()
    source_raw = request.form.get("from", "")
    destination_raw = request.form.get("to", "")
    source = station_code(source_raw)
    destination = station_code(destination_raw)
    travel_date = request.form.get("date") or date.today().isoformat()
    quota = request.form.get("quota", "General")

    results = [
        train
        for train in TRAINS
        if (not source or train["from"] == source) and (not destination or train["to"] == destination)
    ]

    connection = db()
    inventory = {}
    for t in results:
        key = f"{t['id']}:{travel_date}"
        inventory[key] = availability_for_selection(connection, t['id'], travel_date)
    connection.close()

    return render_template(
        "index.html",
        trains=TRAINS,
        stations=STATIONS,
        class_names=CLASS_NAMES,
        today=date.today().isoformat(),
        bookings=recent_bookings(user["id"] if user else None),
        user=user,
        results=results,
        display_trains=results,
        searched=True,
        search_meta={
            "from": station_label(source) if source else source_raw,
            "to": station_label(destination) if destination else destination_raw,
            "from_code": source,
            "to_code": destination,
            "date": travel_date,
            "quota": quota,
        },
        inventory=inventory,
    )



@app.route("/book/<train_id>/<class_key>", methods=["GET", "POST"])
def book(train_id, class_key):
    user = current_user()
    if not user:
        flash("Booking ke liye pehle login ya register karein.", "error")
        return redirect(url_for("register"))

    train = find_train(train_id)
    if not train or class_key not in train["classes"]:
        return redirect(url_for("index"))

    if request.method == "GET":
        passengers = max(1, min(6, int(request.args.get("passengers", 1))))
        fare = price_for(train, class_key, passengers)
        return render_template(
            "book.html",
            train=train,
            class_key=class_key,
            class_name=CLASS_NAMES[class_key],
            fare=fare,
            passengers=passengers,
            travel_date=request.args.get("date", date.today().isoformat()),
            user=user,
        )

    # POST: passenger_count can be changed via select + auto submit.
    try:
        expected_passengers = int(request.form.get("passenger_count", request.form.get("passengers", "1")))
    except ValueError:
        expected_passengers = 1
    expected_passengers = max(1, min(6, expected_passengers))


    # Passenger count should be driven by the UI.
    # (Add Passenger Details button updates GET param `passengers`.
    # For safety we also read a hidden value for POST.)
    try:
        expected_passengers = int(request.form.get("passengers_count_for_post", request.form.get("passenger_count", expected_passengers)))
    except Exception:
        expected_passengers = int(expected_passengers)
    expected_passengers = max(1, min(6, expected_passengers))



    names = [name.strip() for name in request.form.getlist("passenger_name") if name.strip()]
    # Fallback: If browser returns only 1 passenger_name even when UI shows more,
    # replicate first passenger name so we still create N passenger booking rows.
    if not names:
        names = [user["name"]]

    if len(names) != expected_passengers:
        if len(names) == 1 and expected_passengers > 1:
            names = [names[0] for _ in range(expected_passengers)]
        else:
            # Hard validation fail to avoid silent incorrect booking.
            flash(f"Please enter details for exactly {expected_passengers} passengers.", "error")
            connection.close()
            return render_template(
                "book.html",
                train=train,
                class_key=class_key,
                class_name=CLASS_NAMES[class_key],
                fare=price_for(train, class_key, expected_passengers),
                passengers=expected_passengers,
                travel_date=request.form.get("journey_date", date.today().isoformat()),
                user=user,
            )

    passengers = expected_passengers
    fare = price_for(train, class_key, passengers)



    journey_date = request.form.get("journey_date", date.today().isoformat())

    connection = db()

    # Ensure inventory exists (in case user books for a date we haven't seen yet).
    connection.execute(
        """
        INSERT OR IGNORE INTO seat_inventory
        (train_id, journey_date, class_key, confirmed_remaining, waitlist_capacity, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            train["id"],
            journey_date,
            class_key,
            train["classes"][class_key][1],
            waitlist_capacity_for_confirmed(train["classes"][class_key][1]),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )

    row = connection.execute(
        """
        SELECT confirmed_remaining, waitlist_capacity
        FROM seat_inventory
        WHERE train_id = ? AND journey_date = ? AND class_key = ?
        """,
        (train["id"], journey_date, class_key),
    ).fetchone()

    confirmed_remaining = int(row["confirmed_remaining"]) if row else 0
    waitlist_capacity = int(row["waitlist_capacity"]) if row else 0

    pnr = "PNR" + str(randint(1000000000, 9999999999))

    # Simple realistic rule:
    # - If enough confirmed seats, allocate from confirmed pool and mark booking confirmed.
    # - Otherwise put whole booking into waitlist.
    if confirmed_remaining >= passengers:
        status = "confirmed"
        alloc_from_confirmed = passengers
        new_confirmed_remaining = confirmed_remaining - alloc_from_confirmed
        # Deterministic seat labels for this booking instance.
        seats = [f"{class_key}{1}-{i}" for i in range(confirmed_remaining - alloc_from_confirmed + 1, confirmed_remaining + 1)]
    else:
        status = "waitlisted"
        # Assign waitlist seats as placeholder labels.
        # (They become real/confirmed upon promotion.)
        seats = [f"WL{class_key}{i}" for i in range(1, passengers + 1)]
        new_confirmed_remaining = confirmed_remaining

    connection.execute(
        """
        UPDATE seat_inventory
        SET confirmed_remaining = ?, updated_at = ?
        WHERE train_id = ? AND journey_date = ? AND class_key = ?
        """,
        (new_confirmed_remaining, datetime.now().isoformat(timespec="seconds"), train["id"], journey_date, class_key),
    )

    booking = {
        "pnr": pnr,
        "train": train["name"],
        "route": f"{train['from_name']} to {train['to_name']}",
        "date": journey_date,
        "class": class_key,
        "passengers": names,
        "amount": fare["total"],
        "status": status,
        "seats": seats,
    }

    connection.execute(
        """
        INSERT INTO bookings
        (user_id, pnr, train_id, train_name, route, journey_date, class_key, passengers, seats, amount, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            user["id"],
            pnr,
            train["id"],
            train["name"],
            booking["route"],
            booking["date"],
            class_key,
            json.dumps(names),
            json.dumps(seats),
            fare["total"],
            status,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )

    connection.commit()
    connection.close()

    return render_template(
        "ticket.html",
        train=train,
        booking=booking,
        class_name=CLASS_NAMES[class_key],
        fare=fare,
        user=user,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user():
            return redirect(url_for("index"))
        return render_template("auth.html", mode="login", user=current_user())

    identity = request.form.get("identity", "").strip().lower()
    password = request.form.get("password", "")
    connection = db()
    user = connection.execute(
        "SELECT * FROM users WHERE lower(email) = ? OR mobile = ?",
        (identity, identity),
    ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        connection.close()
        flash("Login details galat hain.", "error")
        return redirect(url_for("index"))

    # Hardening: ensure demo admin always has role='admin'
    if user["email"].lower() == "admin@railconnect.test":
        connection.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user["id"],))
        connection.commit()
        user = connection.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

    connection.close()
    session["user_id"] = user["id"]

    flash("Login successful.", "success")

    # If admin user, redirect directly to admin dashboard.
    if user["role"] == "admin":
        connection = db()
        fresh = connection.execute("SELECT role FROM users WHERE id = ?", (user["id"],)).fetchone()
        connection.close()
        if fresh and fresh["role"] == "admin":
            return redirect(url_for("admin"))

    return redirect(url_for("index"))



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if current_user():
            return redirect(url_for("index"))
        return render_template("auth.html", mode="register", user=current_user())

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    if not name or not email or not mobile or not password:
        flash("Register form ke sab fields bharna zaroori hai.", "error")
        return redirect(url_for("index"))
    if password != confirm:
        flash("Password aur confirm password match nahi ho rahe.", "error")
        return redirect(url_for("index"))

    connection = db()
    try:
        cursor = connection.execute(
            """
            INSERT INTO users (name, email, mobile, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                mobile,
                generate_password_hash(password),
                "user",
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        connection.commit()
        session["user_id"] = cursor.lastrowid

        # If registration created an admin (rare), redirect to admin dashboard.
        user_row = connection.execute("SELECT role FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        if user_row and user_row["role"] == "admin":
            flash("Registration successful. Aap admin dashboard par aa chuke hain.", "success")
            connection.close()
            return redirect(url_for("admin"))

        flash("Registration successful. Aap login ho chuke hain.", "success")
    except sqlite3.IntegrityError:
        flash("Email ya mobile already registered hai.", "error")
    finally:
        connection.close()
    return redirect(url_for("index"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("register"))


@app.get("/my-bookings")
def my_bookings():
    user = current_user()
    if not user:
        flash("My Bookings ke liye pehle login karein.", "error")
        return redirect(url_for("login"))
    connection = db()
    rows = connection.execute(
        "SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC",
        (user["id"],),
    ).fetchall()
    connection.close()
    return render_template("my_bookings.html", bookings=[row_to_booking(row) for row in rows], user=user)


@app.post("/cancel/<pnr>")
def cancel_booking(pnr):
    user = current_user()
    if not user:
        flash("Cancellation ke liye login karein.", "error")
        return redirect(url_for("index"))

    connection = db()

    # Fetch booking details.
    booking_row = connection.execute(
        "SELECT * FROM bookings WHERE lower(pnr) = ? AND user_id = ?",
        (pnr.lower(), user["id"]),
    ).fetchone()

    if not booking_row:
        connection.close()
        flash("Booking not found.", "error")
        return redirect(url_for("my_bookings"))

    if booking_row["status"] == "cancelled":
        connection.close()
        flash("Booking already cancelled.", "info")
        return redirect(url_for("my_bookings"))

    train_id = booking_row["train_id"]
    journey_date = booking_row["journey_date"]
    class_key = booking_row["class_key"]
    passengers = len(json.loads(booking_row["passengers"]))

    # Mark cancelled.
    connection.execute(
        "UPDATE bookings SET status = ? WHERE id = ?",
        ("cancelled", booking_row["id"]),
    )

    # If it was confirmed, free seats and then promote earliest waitlisted bookings.
    if booking_row["status"] == "confirmed":

        inv = connection.execute(
            "SELECT confirmed_remaining, waitlist_capacity FROM seat_inventory WHERE train_id = ? AND journey_date = ? AND class_key = ?",
            (train_id, journey_date, class_key),
        ).fetchone()
        confirmed_remaining = int(inv["confirmed_remaining"]) if inv else 0
        new_confirmed_remaining = confirmed_remaining + passengers

        connection.execute(
            """
            INSERT OR IGNORE INTO seat_inventory (train_id, journey_date, class_key, confirmed_remaining, waitlist_capacity, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (train_id, journey_date, class_key, new_confirmed_remaining, waitlist_capacity_for_confirmed(0), datetime.now().isoformat(timespec="seconds")),
        )

        connection.execute(
            "UPDATE seat_inventory SET confirmed_remaining = ?, updated_at = ? WHERE train_id = ? AND journey_date = ? AND class_key = ?",
            (new_confirmed_remaining, datetime.now().isoformat(timespec="seconds"), train_id, journey_date, class_key),
        )

        # Promote waitlisted bookings in FIFO order.
        while True:
            inv = connection.execute(
                "SELECT confirmed_remaining FROM seat_inventory WHERE train_id = ? AND journey_date = ? AND class_key = ?",
                (train_id, journey_date, class_key),
            ).fetchone()
            confirmed_remaining = int(inv["confirmed_remaining"]) if inv else 0
            if confirmed_remaining <= 0:
                break

            wl = connection.execute(
                """
                SELECT * FROM bookings
                WHERE train_id = ? AND journey_date = ? AND class_key = ? AND status = 'waitlisted'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """,
                (train_id, journey_date, class_key),
            ).fetchone()
            if not wl:
                break

            wl_passengers = len(json.loads(wl["passengers"]))
            if confirmed_remaining < wl_passengers:
                break

            # Allocate seats for promoted booking (simple deterministic seat labels).
            start_index = (confirmed_remaining - wl_passengers) + 1
            seats = [f"{class_key}{start_index + i}-{start_index + i}" for i in range(wl_passengers)]

            connection.execute(
                "UPDATE bookings SET status = ?, seats = ? WHERE id = ?",
                ("confirmed", json.dumps(seats), wl["id"]),
            )
            connection.execute(
                "UPDATE seat_inventory SET confirmed_remaining = ?, updated_at = ? WHERE train_id = ? AND journey_date = ? AND class_key = ?",
                (confirmed_remaining - wl_passengers, datetime.now().isoformat(timespec="seconds"), train_id, journey_date, class_key),
            )

    connection.commit()
    connection.close()

    flash("Booking cancelled. Refund processed (demo).", "success")
    return redirect(url_for("my_bookings"))



@app.get("/admin")
def admin():
    user = current_user()
    if not user or user["role"] != "admin":
        flash("Admin dashboard ke liye admin login chahiye. Demo: admin@railconnect.test / admin123", "error")
        return redirect(url_for("login"))

    connection = db()
    booking_rows = connection.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()
    user_rows = connection.execute(
        """
        SELECT users.*, COUNT(bookings.id) AS booking_count
        FROM users
        LEFT JOIN bookings ON bookings.user_id = users.id
        GROUP BY users.id
        ORDER BY users.id DESC
        """
    ).fetchall()
    connection.close()
    bookings = [row_to_booking(row) for row in booking_rows]
    total_revenue = sum(booking["amount"] for booking in bookings)
    return render_template(
        "admin.html",
        trains=TRAINS,
        bookings=bookings,
        users=user_rows,
        total_revenue=total_revenue,
        user=user,
    )


@app.get("/api/pnr/<pnr>")
def pnr_lookup(pnr):
    connection = db()
