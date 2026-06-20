(function () {
  // Creates a simple Razorpay-like modal UI (no real payments).
  function ensureModal() {
    if (document.getElementById('razorpay-like-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'razorpay-like-modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.innerHTML = `
      <div class="rp-overlay"></div>
      <div class="rp-modal">
        <div class="rp-modal-head">
          <div class="rp-modal-title">RailConnect Payment</div>
          <button type="button" class="rp-close" aria-label="Close">✕</button>
        </div>

        <div class="rp-modal-body">
          <div class="rp-grid">
            <div class="rp-left">
              <div class="rp-method-title">UPI</div>
              <div class="rp-methods" style="display:flex; gap:10px; flex-wrap:wrap;">
                <button type="button" class="rp-chip">UPI</button>
                <button type="button" class="rp-chip">Google Pay</button>
                <button type="button" class="rp-chip">PhonePe</button>
                <button type="button" class="rp-chip">Paytm</button>
              </div>

              <div class="rp-sep"></div>

              <div class="rp-method-title">Cards</div>
              <div class="rp-methods" style="display:flex; gap:10px; flex-wrap:wrap;">
                <button type="button" class="rp-chip">Credit Card</button>
                <button type="button" class="rp-chip">Debit Card</button>
              </div>

              <div class="rp-sep"></div>

              <div class="rp-method-title">Net Banking</div>
              <div class="rp-methods">
                <button type="button" class="rp-chip">Net Banking</button>
              </div>
            </div>

            <div class="rp-right">
              <div class="rp-amount">Pay <span id="rp-amount">₹</span></div>
              <div class="rp-success" id="rp-success" style="display:none; color:green; font-weight:600; margin-top:10px;"></div>
              <div class="rp-processing" id="rp-processing" style="display:none; color:#111; font-weight:600; margin-top:10px;">Processing payment...</div>

              <button type="button" id="rp-pay-now" class="rp-pay">Pay ₹</button>
              <div class="rp-note">Demo checkout. Booking will be created after success.</div>
            </div>
          </div>
        </div>
      </div>
    `;

    // inline styles (minimal)
    const style = document.createElement('style');
    style.textContent = `
      #razorpay-like-modal { position: fixed; inset: 0; z-index: 99999; display: none; }
      #razorpay-like-modal.show { display: block; }
      #razorpay-like-modal .rp-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.45); }
      #razorpay-like-modal .rp-modal { position: relative; width: min(980px, 96vw); margin: 6vh auto; background:#fff; border-radius:14px; box-shadow: 0 10px 30px rgba(0,0,0,0.25); overflow:hidden; border:1px solid rgba(0,0,0,0.08); }
      #razorpay-like-modal .rp-modal-head { display:flex; align-items:center; justify-content:space-between; padding:14px 16px; border-bottom:1px solid #eee; }
      #razorpay-like-modal .rp-modal-title { font-weight:700; }
      #razorpay-like-modal .rp-close { border: none; background: transparent; font-size:18px; cursor:pointer; padding:6px 8px; }
      #razorpay-like-modal .rp-modal-body { padding:16px; }
      #razorpay-like-modal .rp-grid { display:grid; grid-template-columns: 1fr 320px; gap:16px; }
      @media(max-width:860px){ #razorpay-like-modal .rp-grid{ grid-template-columns: 1fr; } }
      #razorpay-like-modal .rp-method-title { font-weight:700; margin-bottom:8px; }
      #razorpay-like-modal .rp-chip { border:1px solid #e5e7eb; background:#f9fafb; border-radius:12px; padding:10px 12px; cursor:pointer; font-weight:600; }
      #razorpay-like-modal .rp-sep { height:12px; }
      #razorpay-like-modal .rp-amount { font-size:22px; font-weight:800; margin-top:4px; }
      #razorpay-like-modal .rp-pay { width:100%; margin-top:14px; padding:12px 14px; border:none; border-radius:12px; background:#0d6efd; color:#fff; font-weight:800; cursor:pointer; }
      #razorpay-like-modal .rp-note { margin-top:10px; color:#6b7280; font-size:12px; }
    `;
    document.head.appendChild(style);

    const closeBtn = modal.querySelector('.rp-close');
    const overlay = modal.querySelector('.rp-overlay');
    const hide = () => modal.classList.remove('show');
    closeBtn?.addEventListener('click', hide);
    overlay?.addEventListener('click', hide);

    modal.dataset.hide = 'true';
    document.body.appendChild(modal);
  }

  function openModal(amountINR, form) {
    ensureModal();
    const modal = document.getElementById('razorpay-like-modal');
    const amountEl = modal.querySelector('#rp-amount');
    const payBtn = modal.querySelector('#rp-pay-now');
    const processing = modal.querySelector('#rp-processing');
    const success = modal.querySelector('#rp-success');

    amountEl.textContent = amountINR;
    payBtn.textContent = `Pay ₹${amountINR}`;

    modal.classList.add('show');

    const handler = () => {
      payBtn.disabled = true;
      processing.style.display = 'block';
      success.style.display = 'none';

      setTimeout(() => {
        processing.style.display = 'none';
        success.style.display = 'block';
        success.textContent = '✅ Payment Successful';

        // Close modal a bit later, then submit.
        setTimeout(() => {
          modal.classList.remove('show');
          // ensure real submit uses existing hidden fields
          form.submit();
        }, 500);
      }, 1100);
    };

    payBtn.onclick = handler;
  }

  // Hook to existing book page button.
  function init() {
    const payBtn = document.getElementById('payBtn');
    if (!payBtn) return;
    const form = payBtn.closest('form');
    const payStatus = document.getElementById('payStatus');

    // amount is inside button text like: "Pay Rs. 123 and Book"
    const raw = payBtn.textContent || '';
    const match = raw.match(/Rs\.\s*([0-9,]+)/i) || raw.match(/₹\s*([0-9,]+)/i);
    const amount = match ? match[1].replace(/,/g, '') : '1500';

    payBtn.addEventListener('click', (e) => {
      e.preventDefault();
      payStatus && (payStatus.textContent = '');
      openModal(amount, form);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

