// Razorpay/Real UI integration is not possible without a backend that creates an Order
// and verifies payment signature. This file keeps a realistic UI flow for demo.

(function () {
  const payBtn = document.getElementById('payBtn');
  const payStatus = document.getElementById('payStatus');
  const form = payBtn ? payBtn.closest('form') : null;

  if (!payBtn || !payStatus || !form) return;

  payBtn.addEventListener('click', (e) => {
    e.preventDefault();

    payBtn.disabled = true;
    payBtn.style.opacity = 0.7;

    payStatus.textContent = 'Opening payment gateway...';
    payStatus.style.color = '#111';

    // Demo flow: show modal-like steps, then submit.
    setTimeout(() => {
      payStatus.textContent = 'Processing payment...';
      payStatus.style.color = '#111';
    }, 300);

    setTimeout(() => {
      payStatus.textContent = 'Payment successful. Booking confirmed.';
      payStatus.style.color = 'green';
      form.submit();
    }, 1400);
  });
})();


