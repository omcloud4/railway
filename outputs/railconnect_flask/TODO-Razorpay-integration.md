# Razorpay integration checklist (RailConnect)

## Goal
- Real Razorpay Checkout UI (no fake payment)
- Payment signature verification succeeds => booking confirmed
- Use Razorpay Order API

## Steps
1. Install dependency `razorpay` (and/or add requests if needed).
2. Add config/env reads in `app.py`:
   - `RAZORPAY_KEY_ID`
   - `RAZORPAY_KEY_SECRET`
   - `RAZORPAY_API_BASE` (optional)
3. Add `/create-order` endpoint:
   - input: amount, currency (INR)
   - output: order_id, key_id
4. Change `book.html`/JS flow:
   - pay button opens Razorpay Checkout using order_id
   - on success, send payment_id, order_id, signature to `/verify-payment`
5. Add `/verify-payment` endpoint:
   - verify signature using key_secret
   - if ok: finalize booking (seat inventory allocation + insert booking)
   - else: return failure
6. Refactor `/book/...` so it no longer creates booking immediately on POST; it should create a “pending hold” record or delay booking finalization.
7. Update UI messaging + disable button during checkout.
8. Manual test using Razorpay **test keys**:
   - success payment => ticket page shows confirmed
   - failure/cancel => no booking created

