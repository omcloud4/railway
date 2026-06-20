## RailConnect: AWS RDS (PostgreSQL) setup – progress tracker

- [ ] Inspect app.py DB SQL paths (SQLite vs Postgres)
- [x] Update `outputs/railconnect_flask/app.py` to use Postgres-compatible SQL (`ON CONFLICT`, `%s` placeholders)

- [x] Ensure Postgres init/seed works in `init_db()` (admin + seat_inventory horizon)

- [ ] Ensure booking/cancel inventory insert uses Postgres syntax

- [ ] (Optional) Update README with RDS env vars + TLS notes
- [ ] Run local verification using a real Postgres (or AWS RDS) via `PG_DSN`

