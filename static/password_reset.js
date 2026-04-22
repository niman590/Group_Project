document.addEventListener("DOMContentLoaded", function () {
  const emailInput = document.querySelector('input[name="email"]');
  const otpInput = document.querySelector('input[name="otp"]');
  const newPasswordInput = document.querySelector('input[name="new_password"]');
  const confirmPasswordInput = document.querySelector('input[name="confirm_password"]');

  const sendBtn = document.getElementById("sendOtpBtn");
  const verifyBtn = document.getElementById("verifyOtpBtn");
  const form = document.getElementById("resetForm");
  const formMessage = document.getElementById("form-message");
  const resetSubmitBtn = document.getElementById("resetSubmitBtn");
  const strengthText = document.getElementById("passwordStrengthText");
  const passwordToggles = document.querySelectorAll(".password-toggle");

  const pageLoggedIn = document.body.dataset.resetLoggedIn === "true";
  const returnUrl = document.body.dataset.resetReturnUrl || "/login";

  function showMessage(message, type = "error") {
    formMessage.textContent = message;
    formMessage.className = `form-message ${type}`;
    formMessage.style.display = "block";
  }

  function clearMessage() {
    formMessage.textContent = "";
    formMessage.className = "form-message";
    formMessage.style.display = "none";
  }

  function setButtonLoading(button, loadingText) {
    if (!button) return;
    button.dataset.originalText = button.textContent;
    button.textContent = loadingText;
    button.classList.add("loading");
  }

  function clearButtonLoading(button) {
    if (!button) return;
    if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
    }
    button.classList.remove("loading");
  }

  function getPasswordStrength(password) {
    let score = 0;
    if (password.length >= 8) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[a-z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;

    if (!password) return { label: "—", tone: "" };
    if (score <= 2) return { label: "Weak", tone: "warning" };
    if (score === 3 || score === 4) return { label: "Medium", tone: "success" };
    return { label: "Strong", tone: "success" };
  }

  function updatePasswordStrength() {
    if (!strengthText || !newPasswordInput) return;
    const result = getPasswordStrength(newPasswordInput.value.trim());
    strengthText.textContent = `Password strength: ${result.label}`;
    strengthText.style.color =
      result.tone === "warning" ? "#b26a00" :
      result.tone === "success" ? "#1f7a46" :
      "#66758c";
  }

  passwordToggles.forEach((toggle) => {
    toggle.addEventListener("click", function () {
      const targetId = this.getAttribute("data-target");
      const input = document.getElementById(targetId);
      if (!input) return;

      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      this.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");

      const icon = this.querySelector("i");
      if (icon) {
        icon.className = isPassword ? "fa-regular fa-eye-slash" : "fa-regular fa-eye";
      }
    });
  });

  if (newPasswordInput) {
    newPasswordInput.addEventListener("input", updatePasswordStrength);
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", async () => {
      const email = emailInput.value.trim();
      clearMessage();

      if (!email) {
        showMessage("Please enter your email", "error");
        return;
      }

      try {
        setButtonLoading(sendBtn, "Sending...");
        const res = await fetch("/send-otp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email })
        });

        const data = await res.json();

        if (data.success) {
          showMessage("OTP sent to your email", "success");
        } else {
          showMessage(data.message || "Error sending OTP", "error");
        }
      } catch (error) {
        showMessage("Something went wrong while sending OTP", "error");
      } finally {
        clearButtonLoading(sendBtn);
      }
    });
  }

  if (verifyBtn) {
    verifyBtn.addEventListener("click", async () => {
      const otp = otpInput.value.trim();
      clearMessage();

      if (!otp) {
        showMessage("Please enter OTP", "error");
        return;
      }

      try {
        setButtonLoading(verifyBtn, "Verifying...");
        const res = await fetch("/verify-otp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ otp })
        });

        const data = await res.json();

        if (data.success) {
          showMessage("OTP verified successfully", "success");
        } else {
          showMessage(data.message || "Invalid OTP", "error");
        }
      } catch (error) {
        showMessage("Something went wrong while verifying OTP", "error");
      } finally {
        clearButtonLoading(verifyBtn);
      }
    });
  }

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearMessage();

      const newPassword = newPasswordInput.value.trim();
      const confirmPassword = confirmPasswordInput.value.trim();

      if (!newPassword || !confirmPassword) {
        showMessage("Please fill all fields", "error");
        return;
      }

      if (newPassword !== confirmPassword) {
        showMessage("Passwords do not match", "error");
        return;
      }

      try {
        if (resetSubmitBtn) {
          resetSubmitBtn.classList.add("loading");
          const btnText = resetSubmitBtn.querySelector(".btn-text");
          if (btnText) {
            btnText.textContent = "Resetting...";
          }
        }

        const res = await fetch("/reset-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ new_password: newPassword })
        });

        const data = await res.json();

        if (data.success) {
          showMessage("Password reset successful!", "success");
          setTimeout(() => {
            window.location.href = pageLoggedIn ? returnUrl : "/login";
          }, 1200);
        } else {
          showMessage(data.message || "Error resetting password", "error");
        }
      } catch (error) {
        showMessage("Something went wrong while resetting password", "error");
      } finally {
        if (resetSubmitBtn) {
          resetSubmitBtn.classList.remove("loading");
          const btnText = resetSubmitBtn.querySelector(".btn-text");
          if (btnText) {
            btnText.textContent = "Reset Password";
          }
        }
      }
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "/" && document.activeElement !== emailInput && emailInput) {
      const tag = document.activeElement ? document.activeElement.tagName : "";
      if (tag !== "INPUT" && tag !== "TEXTAREA") {
        event.preventDefault();
        emailInput.focus();
      }
    }
  });

  updatePasswordStrength();
});