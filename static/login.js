document.addEventListener("DOMContentLoaded", function () {
  const passwordInput = document.getElementById("password");
  const passwordToggle = document.getElementById("passwordToggle");
  const loginForm = document.getElementById("loginForm");
  const loginSubmitBtn = document.getElementById("loginSubmitBtn");
  const flashMessages = document.querySelectorAll("[data-flash]");
  const flashCloseButtons = document.querySelectorAll("[data-flash-close]");
  const nicInput = document.getElementById("nic");

  function hideFlash(flash, duration = 250) {
    if (!flash) return;
    flash.style.transition = `opacity ${duration}ms ease, transform ${duration}ms ease`;
    flash.style.opacity = "0";
    flash.style.transform = "translateY(-6px)";
    setTimeout(() => {
      if (flash.parentNode) {
        flash.remove();
      }
    }, duration);
  }

  if (passwordToggle && passwordInput) {
    passwordToggle.addEventListener("click", function () {
      const isPassword = passwordInput.type === "password";
      passwordInput.type = isPassword ? "text" : "password";
      this.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");

      const icon = this.querySelector("i");
      if (icon) {
        icon.className = isPassword ? "fa-regular fa-eye-slash" : "fa-regular fa-eye";
      }
    });
  }

  if (loginForm && loginSubmitBtn) {
    loginForm.addEventListener("submit", function () {
      if (nicInput) {
        nicInput.value = nicInput.value.trim();
      }

      loginSubmitBtn.classList.add("loading");
      const btnText = loginSubmitBtn.querySelector(".btn-text");
      if (btnText) {
        btnText.textContent = "Signing in...";
      }
    });
  }

  flashMessages.forEach((flash) => {
    setTimeout(() => {
      if (flash.parentNode) {
        hideFlash(flash, 300);
      }
    }, 4500);
  });

  flashCloseButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const flash = this.closest("[data-flash]");
      hideFlash(flash, 250);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "/" && document.activeElement !== nicInput && nicInput) {
      const tag = document.activeElement ? document.activeElement.tagName : "";
      if (tag !== "INPUT" && tag !== "TEXTAREA") {
        event.preventDefault();
        nicInput.focus();
      }
    }
  });
});