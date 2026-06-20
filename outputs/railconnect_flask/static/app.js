const loginModal = document.querySelector("#loginModal");
const registerModal = document.querySelector("#registerModal");
const openLogin = document.querySelectorAll("[data-open-login]");
const openRegister = document.querySelectorAll("[data-open-register]");
const closeLogin = document.querySelector("[data-close-login]");
const closeRegister = document.querySelector("[data-close-register]");
const switchRegister = document.querySelector("[data-switch-register]");
const switchLogin = document.querySelector("[data-switch-login]");

openLogin.forEach((button) => {
  button.addEventListener("click", () => {
    registerModal?.classList.remove("open");
    loginModal?.classList.add("open");
  });
});

openRegister.forEach((button) => {
  button.addEventListener("click", () => {
    loginModal?.classList.remove("open");
    registerModal?.classList.add("open");
  });
});

if (closeLogin) {
  closeLogin.addEventListener("click", () => loginModal.classList.remove("open"));
}

if (closeRegister) {
  closeRegister.addEventListener("click", () => registerModal.classList.remove("open"));
}

if (switchRegister) {
  switchRegister.addEventListener("click", () => {
    loginModal?.classList.remove("open");
    registerModal?.classList.add("open");
  });
}

if (switchLogin) {
  switchLogin.addEventListener("click", () => {
    registerModal?.classList.remove("open");
    loginModal?.classList.add("open");
  });
}

if (loginModal) {
  loginModal.addEventListener("click", (event) => {
    if (event.target === loginModal) loginModal.classList.remove("open");
  });
}

if (registerModal) {
  registerModal.addEventListener("click", (event) => {
    if (event.target === registerModal) registerModal.classList.remove("open");
  });
}

const swapButton = document.querySelector("[data-swap-stations]");
if (swapButton) {
  swapButton.addEventListener("click", () => {
    const from = document.querySelector('input[name="from"]');
    const to = document.querySelector('input[name="to"]');
    const current = from.value;
    from.value = to.value;
    to.value = current;
  });
}

document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-filter]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const filter = button.dataset.filter;
    document.querySelectorAll(".train-card").forEach((card) => {
      const show = filter === "all" || card.dataset.trainType === filter;
      card.style.display = show ? "" : "none";
    });
  });
});

const pnrButton = document.querySelector("#pnrButton");
if (pnrButton) {
  pnrButton.addEventListener("click", async () => {
    const input = document.querySelector("#pnrInput");
    const result = document.querySelector("#pnrResult");
    const pnr = input.value.trim();
    if (!pnr) {
      result.textContent = "Please enter a PNR number.";
      return;
    }

    result.textContent = "Checking...";
    try {
      const response = await fetch(`/api/pnr/${encodeURIComponent(pnr)}`);
      const data = await response.json();
      if (!data.found) {
        result.textContent = "PNR not found in demo records.";
        return;
      }
      const booking = data.booking;
      result.innerHTML = `<strong>${booking.status.toUpperCase()}</strong><br>${booking.train}<br>${booking.route}<br>Seat: ${booking.seats.join(", ")}`;
    } catch (error) {
      result.textContent = "Unable to check PNR right now.";
    }
  });
}
