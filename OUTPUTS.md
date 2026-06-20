Planned implementation next:
1) Modify `outputs/railconnect_flask/app.py`:
   - Extend SQLite schema with seat inventory + waitlist
   - Implement inventory initialization from TRAINS classes counts
   - Update /book to allocate seats or create waitlisted booking
   - Update /cancel to free seats and promote waitlisted bookings
2) Update templates to display live availability/WL where relevant.
3) Run quick smoke test.

