# Backend implementation checklist (seat inventory)

## DB
- [ ] Add table `seat_inventory` (train_id, class_key, confirmed_remaining, waitlist_capacity, updated_at)
- [ ] Add table `booking_allocation` or store allocation inside bookings.seats + status + seat_statuses
- [ ] Ensure schema migration for existing DB.

## Init
- [ ] Seed seat inventory from TRAINS[*]['classes'][class_key][1] (confirmed) and set waitlist cap.

## Booking flow
- [ ] Lock transaction
- [ ] Compute availability for journey_date/train_id/class_key
- [ ] If enough confirmed seats => status=confirmed
- [ ] Else => status=waitlisted and allocate placeholder waitlist seat ids

## Cancellation flow
- [ ] Update booking status to cancelled
- [ ] Free allocated confirmed seats (if confirmed)
- [ ] Promote earliest waitlisted bookings for same train+class+date

## PNR lookup
- [ ] Return seats + status correctly

