import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from random import randint

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = "railconnect-demo-secret"
BASE_DIR = Path(__file__).resolve().parent
schema_path = BASE_DIR / "schema-postgres.sql"


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


def is_postgres():
    # Postgres-only mode
    return True



def ensure_schema_and_admin_seed(connection):
    """Ensure schema exists and seed demo admin + one demo booking."""

    if is_postgres():
        # Create tables if missing (idempotent)
        schema_path = BASE_DIR / "schema-postgres.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        with connection.cursor() as cur:
            cur.execute(schema_sql)

        # psycopg2 doesn't return dict rows by default; use cursor.fetchall mapping via columns not needed here.
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM users WHERE email = %s",
                ("admin@railconnect.test",),
            )
            admin_row = cur.fetchone()
        admin_id = admin_row[0] if admin_row else None

        if not admin_id:
            admin_hash = generate_password_hash("admin123")
            with connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (name, email, mobile, password_hash, role, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        "RailConnect Admin",
                        "admin@railconnect.test",
                        "9999999999",
                        admin_hash,
                        "admin",
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
                admin_id = cur.fetchone()[0]

        with connection.cursor() as cur:
            cur.execute("SELECT id FROM bookings WHERE pnr = %s", ("PNR5628139042",))
            existing = cur.fetchone()

        if not existing:
            # demo booking
            passengers = ["Rahul Sharma", "Priya Sharma"]
            seats = ["B1-21", "B1-22"]
            with connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bookings
                    (user_id, pnr, train_id, train_name, route, journey_date, class_key, passengers, seats, amount, status, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)
                    """,
                    (
                        admin_id,
                        "PNR5628139042",
                        "12301",
                        "Rajdhani Express",
                        "New Delhi to Howrah",
                        "2026-06-18",
                        "3A",
                        json.dumps(passengers),
                        json.dumps(seats),
                        4050,
                        "confirmed",
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )

        connection.commit()
        return

    # SQLite schema path (keep original behavior)
    # Create tables if missing (simple executescript)
    cursor = connection.cursor()
    cursor.executescript(
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

    connection.commit()


def db():
    import psycopg2

    return psycopg2.connect(
        host="database-1.cluster-cvkcs4q28uf5.ap-south-1.rds.amazonaws.com",
        port=5432,
        database="postgres",
        user="postgres",
        password="rootomj3",
        sslmode="require"
    )




def ensure_seat_inventory(connection):
    """Seed seat inventory for all trains/classes across near-future dates."""


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

    if is_postgres():
        # Postgres UPSERT/DO NOTHING
        with connection.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO seat_inventory (train_id, journey_date, class_key, confirmed_remaining, waitlist_capacity, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (train_id, journey_date, class_key) DO NOTHING
                """,
                rows_to_insert,
            )
    else:
        connection.executemany(
            """
            INSERT OR IGNORE INTO seat_inventory
            (train_id, journey_date, class_key, confirmed_remaining, waitlist_capacity, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert,
        )


def init_db():
    connection = db()
    try:
        ensure_schema_and_admin_seed(connection)
        # Seed seat inventory after schema is ready
        ensure_seat_inventory(connection)
        connection.commit()
    finally:
        connection.close()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    connection = db()
    if is_postgres():
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            # columns: id, name, email, mobile, password_hash, role, created_at
            user = {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "mobile": row[3],
                "password_hash": row[4],
                "role": row[5],
                "created_at": row[6],
            }
    else:
        user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        user = dict(user) if user else None

    connection.close()
    return user


def row_to_booking(row):
    # Works for SQLite row_factory Row and for Postgres dict-like conversion via indexes.
    if is_postgres():
        # bookings columns order from schema-postgres.sql:
        # id, user_id, pnr, train_id, train_name, route, journey_date, class_key, passengers, seats, amount, status, created_at
        return {
            "pnr": row[2],
            "train": row[4],
            "route": row[5],
            "date": row[6],
            "class": row[7],
            "passengers": json.loads(row[8]) if isinstance(row[8], str) else row[8],
            "amount": row[10],
            "status": row[11],
            "seats": json.loads(row[9]) if isinstance(row[9], str) else row[9],
        }

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
    if is_postgres():
        with connection.cursor() as cur:
            if user_id:
                cur.execute(
                    "SELECT * FROM bookings WHERE user_id = %s ORDER BY id DESC LIMIT %s",
                    (user_id, limit),
                )
            else:
                cur.execute("SELECT * FROM bookings ORDER BY id DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
    else:
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
    if is_postgres():
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT class_key, confirmed_remaining
                FROM seat_inventory
                WHERE train_id = %s AND journey_date = %s
                """,
                (train_id, journey_date),
            )
            inv_rows = cur.fetchall()

            cur.execute(
                """
                SELECT class_key, COUNT(*) AS cnt
                FROM bookings
                WHERE train_id = %s AND journey_date = %s AND status = 'waitlisted'
                GROUP BY class_key
                """,
                (train_id, journey_date),
            )
            wl_rows = cur.fetchall()

        inv_map = {r[0]: int(r[1]) for r in inv_rows}
        wl_map = {r[0]: int(r[1]) for r in wl_rows}
    else:
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
        wl_map = {r["class_key"]: int(r["cnt"]) for r in wl_rows}

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
        inv = availability_for_selection(connection, t["id"], today)
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
        inventory[key] = availability_for_selection(connection, t["id"], travel_date)
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

    # POST
    try:
        expected_passengers = int(request.form.get("passenger_count", request.form.get("passengers", "1")))
    except ValueError:
        expected_passengers = 1
    expected_passengers = max(1, min(6, expected_passengers))

    try:
        expected_passengers = int(
            request.form.get(
                "passengers_count_for_post",
                request.form.get("passenger_count", expected_passengers),
            )
        )
    except Exception:
        expected_passengers = int(expected_passengers)
    expected_passengers = max(1, min(6, expected_passengers))

    names = [name.strip() for name in request.form.getlist("passenger_name") if name.strip()]
    if not names:
        names = [user["name"]]

    if len(names) != expected_passengers:
        if len(names) == 1 and expected_passengers > 1:
            names = [names[0] for _ in range(expected_passengers)]
        else:
            flash(f"Please enter details for exactly {expected_passengers} passengers.", "error")
            connection = db()
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

    # Ensure inventory row exists for this train/date/class
    if is_postgres():
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO seat_inventory (train_id, journey_date, class_key, confirmed_remaining, waitlist_capacity, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (train_id, journey_date, class_key) DO NOTHING
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
            cur.execute(
                """
                SELECT confirmed_remaining, waitlist_capacity
                FROM seat_inventory
                WHERE train_id = %s AND journey_date = %s AND class_key = %s
                """,
                (train["id"], journey_date, class_key),
            )
            row = cur.fetchone()
            confirmed_remaining = int(row[0]) if row else 0
            waitlist_capacity = int(row[1]) if row else 0
    else:
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

    if confirmed_remaining >= passengers:
        status = "confirmed"
        new_confirmed_remaining = confirmed_remaining - passengers
        seats = [f"{class_key}{1}-{i}" for i in range(confirmed_remaining - passengers + 1, confirmed_remaining + 1)]
    else:
        status = "waitlisted"
        seats = [f"WL{class_key}{i}" for i in range(1, passengers + 1)]
        new_confirmed_remaining = confirmed_remaining

    # update inventory
    if is_postgres():

        with connection.cursor() as cur:
            cur.execute(
                """
                UPDATE seat_inventory
                SET confirmed_remaining = %s, updated_at = %s
                WHERE train_id = %s AND journey_date = %s AND class_key = %s
                """,
                (
                    new_confirmed_remaining,
                    datetime.now().isoformat(timespec="seconds"),
                    train["id"],
                    journey_date,
                    class_key,
                ),
            )
            cur.execute(
                """
                INSERT INTO bookings
                (user_id, pnr, train_id, train_name, route, journey_date, class_key, passengers, seats, amount, status, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)
                """,
                (
                    user["id"],
                    pnr,
                    train["id"],
                    train["name"],
                    f"{train['from_name']} to {train['to_name']}",
                    journey_date,
                    class_key,
                    json.dumps(names),
                    json.dumps(seats),
                    fare["total"],
                    status,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
    else:
        connection.execute(
            """
            UPDATE seat_inventory
            SET confirmed_remaining = ?, updated_at = ?
            WHERE train_id = ? AND journey_date = ? AND class_key = ?
            """,
            (
                new_confirmed_remaining,
                datetime.now().isoformat(timespec="seconds"),
                train["id"],
                journey_date,
                class_key,
            ),
        )
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
                f"{train['from_name']} to {train['to_name']}",
                journey_date,
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

    return render_template(
        "ticket.html",
        train=train,
        booking=booking,
        class_name=CLASS_NAMES[class_key],
        fare=fare,
        user=user,
    )


def price_for(train, class_key, passengers):
    fare = train["classes"][class_key][0]
    base = fare * passengers
    tax = round(base * 0.05)
    convenience = 35
    return {"base": base, "tax": tax, "convenience": convenience, "total": base + tax + convenience}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user():
            return redirect(url_for("index"))
        return render_template("auth.html", mode="login", user=current_user())

    identity = request.form.get("identity", "").strip().lower()
    password = request.form.get("password", "")

    connection = db()
    if is_postgres():
        with connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE lower(email) = %s OR mobile = %s",
                (identity, identity),
            )
            user_row = cur.fetchone()
        # columns: id, name, email, mobile, password_hash, role, created_at
        user = None
        if user_row:
            user = {
                "id": user_row[0],
                "name": user_row[1],
                "email": user_row[2],
                "mobile": user_row[3],
                "password_hash": user_row[4],
                "role": user_row[5],
                "created_at": user_row[6],
            }
    else:
        user = connection.execute(
            "SELECT * FROM users WHERE lower(email) = ? OR mobile = ?",
            (identity, identity),
        ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        connection.close()
        flash("Login details galat hain.", "error")
        return redirect(url_for("index"))

    # Ensure demo admin role
    if user["email"].lower() == "admin@railconnect.test":
        if is_postgres():
            with connection.cursor() as cur:
                cur.execute("UPDATE users SET role = 'admin' WHERE id = %s", (user["id"],))
            connection.commit()
            with connection.cursor() as cur:
                cur.execute("SELECT role FROM users WHERE id = %s", (user["id"],))
                fresh = cur.fetchone()
            user["role"] = fresh[0] if fresh else "admin"
        else:
            connection.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user["id"],))
            connection.commit()
            user = connection.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

    connection.close()
    session["user_id"] = user["id"]

    flash("Login successful.", "success")

    if user["role"] == "admin":
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
        created_at = datetime.now().isoformat(timespec="seconds")
        pw_hash = generate_password_hash(password)

        if is_postgres():
            with connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (name, email, mobile, password_hash, role, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (name, email, mobile, pw_hash, "user", created_at),
                )
                new_id = cur.fetchone()[0]
            connection.commit()
        else:
            cursor = connection.execute(
                """
                INSERT INTO users (name, email, mobile, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, email, mobile, pw_hash, "user", created_at),
            )
            connection.commit()
            new_id = cursor.lastrowid

        session["user_id"] = new_id
        flash("Registration successful. Aap login ho chuke hain.", "success")
    except Exception:
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

    rows = recent_bookings(user["id"], limit=50)
    return render_template("my_bookings.html", bookings=rows, user=user)


@app.post("/cancel/<pnr>")
def cancel_booking(pnr):
    user = current_user()
    if not user:
        flash("Cancellation ke liye login karein.", "error")
        return redirect(url_for("index"))

    connection = db()

    if is_postgres():
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM bookings WHERE lower(pnr) = %s AND user_id = %s", (pnr.lower(), user["id"]))
            booking_row = cur.fetchone()
        if not booking_row:
            connection.close()
            flash("Booking not found.", "error")
            return redirect(url_for("my_bookings"))
        status = booking_row[11]
        train_id = booking_row[3]
        journey_date = booking_row[6]
        class_key = booking_row[7]
        passengers = booking_row[8]
        passengers = len(passengers) if isinstance(passengers, list) else len(json.loads(passengers))
    else:
        booking_row = connection.execute(
            "SELECT * FROM bookings WHERE lower(pnr) = ? AND user_id = ?",
            (pnr.lower(), user["id"]),
        ).fetchone()
        if not booking_row:
            connection.close()
            flash("Booking not found.", "error")
            return redirect(url_for("my_bookings"))
        status = booking_row["status"]
        train_id = booking_row["train_id"]
        journey_date = booking_row["journey_date"]
        class_key = booking_row["class_key"]
        passengers = len(json.loads(booking_row["passengers"]))

    if status == "cancelled":
        connection.close()
        flash("Booking already cancelled.", "info")
        return redirect(url_for("my_bookings"))

    booking_id = booking_row[0] if is_postgres() else booking_row["id"]

    # Mark cancelled
    if is_postgres():
        with connection.cursor() as cur:
            cur.execute("UPDATE bookings SET status = %s WHERE id = %s", ("cancelled", booking_id))
    else:
        connection.execute("UPDATE bookings SET status = ? WHERE id = ?", ("cancelled", booking_id))

    # Promote waitlist if it was confirmed
    if status == "confirmed":
        if is_postgres():
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT confirmed_remaining, waitlist_capacity FROM seat_inventory WHERE train_id=%s AND journey_date=%s AND class_key=%s",
                    (train_id, journey_date, class_key),
                )
                inv = cur.fetchone()
                confirmed_remaining = int(inv[0]) if inv else 0
                new_confirmed_remaining = confirmed_remaining + passengers

                cur.execute(
                    """
                    INSERT INTO seat_inventory (train_id, journey_date, class_key, confirmed_remaining, waitlist_capacity, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (train_id, journey_date, class_key) DO NOTHING
                    """,
                    (
                        train_id,
                        journey_date,
                        class_key,
                        new_confirmed_remaining,
                        waitlist_capacity_for_confirmed(0),
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )

                cur.execute(
                    """
                    UPDATE seat_inventory
                    SET confirmed_remaining=%s, updated_at=%s
                    WHERE train_id=%s AND journey_date=%s AND class_key=%s
                    """,
                    (
                        new_confirmed_remaining,
                        datetime.now().isoformat(timespec="seconds"),
                        train_id,
                        journey_date,
                        class_key,
                    ),
                )

                # FIFO promotion
                while True:
                    cur.execute(
                        "SELECT confirmed_remaining FROM seat_inventory WHERE train_id=%s AND journey_date=%s AND class_key=%s",
                        (train_id, journey_date, class_key),
                    )
                    inv = cur.fetchone()
                    confirmed_remaining = int(inv[0]) if inv else 0
                    if confirmed_remaining <= 0:
                        break

                    cur.execute(
                        """
                        SELECT id, passengers
                        FROM bookings
                        WHERE train_id=%s AND journey_date=%s AND class_key=%s AND status='waitlisted'
                        ORDER BY created_at ASC, id ASC
                        LIMIT 1
                        """,
                        (train_id, journey_date, class_key),
                    )
                    wl = cur.fetchone()
                    if not wl:
                        break
                    wl_id = wl[0]
                    wl_passengers = wl[1]
                    wl_passengers = len(wl_passengers) if isinstance(wl_passengers, list) else len(json.loads(wl_passengers))
                    if confirmed_remaining < wl_passengers:
                        break

                    start_index = (confirmed_remaining - wl_passengers) + 1
                    seats = [f"{class_key}{start_index + i}-{start_index + i}" for i in range(wl_passengers)]

                    cur.execute(
                        "UPDATE bookings SET status=%s, seats=%s::jsonb WHERE id=%s",
                        ("confirmed", json.dumps(seats), wl_id),
                    )
                    cur.execute(
                        """
                        UPDATE seat_inventory
                        SET confirmed_remaining=%s, updated_at=%s
                        WHERE train_id=%s AND journey_date=%s AND class_key=%s
                        """,
                        (
                            confirmed_remaining - wl_passengers,
                            datetime.now().isoformat(timespec="seconds"),
                            train_id,
                            journey_date,
                            class_key,
                        ),
                    )
        else:
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
                (
                    train_id,
                    journey_date,
                    class_key,
                    new_confirmed_remaining,
                    waitlist_capacity_for_confirmed(0),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            connection.execute(
                "UPDATE seat_inventory SET confirmed_remaining = ?, updated_at = ? WHERE train_id = ? AND journey_date = ? AND class_key = ?",
                (new_confirmed_remaining, datetime.now().isoformat(timespec="seconds"), train_id, journey_date, class_key),
            )

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

                start_index = (confirmed_remaining - wl_passengers) + 1
                seats = [f"{class_key}{start_index + i}-{start_index + i}" for i in range(wl_passengers)]

                connection.execute(
                    "UPDATE bookings SET status = ?, seats = ? WHERE id = ?",
                    ("confirmed", json.dumps(seats), wl["id"]),
                )
                connection.execute(
                    "UPDATE seat_inventory SET confirmed_remaining = ?, updated_at = ? WHERE train_id = ? AND journey_date = ? AND class_key = ?",
                    (
                        confirmed_remaining - wl_passengers,
                        datetime.now().isoformat(timespec="seconds"),
                        train_id,
                        journey_date,
                        class_key,
                    ),
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

    if is_postgres():
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM bookings ORDER BY id DESC")
            booking_rows = cur.fetchall()

            cur.execute(
                """
                SELECT users.*, COUNT(bookings.id) AS booking_count
                FROM users
                LEFT JOIN bookings ON bookings.user_id = users.id
                GROUP BY users.id
                ORDER BY users.id DESC
                """
            )
            user_rows = cur.fetchall()

        bookings = [row_to_booking(r) for r in booking_rows]
        total_revenue = sum(b["amount"] for b in bookings)

        # user_rows mapping for template consumption
        # columns: id,name,email,mobile,password_hash,role,created_at,booking_count
        user_rows_out = [
            {
                "id": r[0],
                "name": r[1],
                "email": r[2],
                "mobile": r[3],
                "password_hash": r[4],
                "role": r[5],
                "created_at": r[6],
                "booking_count": r[7],
            }
            for r in user_rows
        ]
    else:
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
        bookings = [row_to_booking(row) for row in booking_rows]
        total_revenue = sum(booking["amount"] for booking in bookings)
        user_rows_out = user_rows

    connection.close()

    return render_template(
        "admin.html",
        trains=TRAINS,
        bookings=bookings,
        users=user_rows_out,
        total_revenue=total_revenue,
        user=user,
    )


@app.get("/api/pnr/<pnr>")
def pnr_lookup(pnr):
    connection = db()

    if is_postgres():
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM bookings WHERE lower(pnr) = %s", (pnr.lower(),))
            row = cur.fetchone()
    else:
        row = connection.execute("SELECT * FROM bookings WHERE lower(pnr) = ?", (pnr.lower(),)).fetchone()

    connection.close()
    if not row:
        return jsonify({"found": False})
    booking = row_to_booking(row)
    return jsonify({"found": True, "booking": booking})


init_db()

if __name__ == "__main__":
    app.run(debug=True)

