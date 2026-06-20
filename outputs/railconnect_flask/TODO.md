# TODO (Razorpay integration)

- [ ] Update `outputs/railconnect_flask/app.py`:
  - [ ] Add Razorpay config via env vars: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_API_BASE`
  - [ ] Add route `/create-order` that creates a Razorpay order using amount and returns `order_id` + `razorpayKeyId`
  - [ ] Add route `/verify-payment` (POST) or handle redirect to verify `razorpay_signature`
  - [ ] Add DB columns/logic if needed to store payment status (pending/paid/failed) or only confirm booking after verify.
  - [ ] Modify `/book/...` POST to create *pending* booking (or hold) until payment verified; then finalize confirmed/waitlisted seat allocation.

- [ ] Update `outputs/railconnect_flask/templates/book.html`:
  - [ ] Include Razorpay Checkout button that calls `/create-order` and opens Razorpay Checkout JS.
  - [ ] Ensure payment form is submitted only after signature verify success.

- [ ] Update `outputs/railconnect_flask/static/payment-modal-ui.js`:
  - [ ] Replace demo modal with real Razorpay Checkout using `checkout.js`.

- [ ] Install dependency `razorpay` (optional) or call Razorpay REST via `requests`.

- [ ] Quick test with Razorpay test keys:
  - [ ] Payment success -> booking created
  - [ ] Payment failure/cancel -> booking not created
