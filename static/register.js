document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("registerForm");

  const firstName = document.getElementById("first_name");
  const lastName = document.getElementById("last_name");
  const nic = document.getElementById("nic");
  const phone = document.getElementById("phone");
  const email = document.getElementById("email");
  const password = document.getElementById("password");
  const confirmPassword = document.getElementById("confirm_password");

  const dobMonth = document.getElementById("dob_month");
  const dobDay = document.getElementById("dob_day");
  const dobYear = document.getElementById("dob_year");
  const dateOfBirth = document.getElementById("date_of_birth");

  const registerSubmitBtn = document.getElementById("registerSubmitBtn");
  const passwordStrengthText = document.getElementById("passwordStrengthText");
  const flashMessages = document.querySelectorAll("[data-flash]");
  const flashCloseButtons = document.querySelectorAll("[data-flash-close]");
  const passwordToggles = document.querySelectorAll(".password-toggle");

  function getErrorElement(input) {
    return input.parentElement.parentElement.querySelector(".error-text") ||
           input.parentElement.querySelector(".error-text");
  }

  function getFieldWrap(input) {
    return input.closest(".input-wrap");
  }

  function setError(input, message) {
    const errorEl = getErrorElement(input);
    const wrap = getFieldWrap(input);

    input.classList.add("input-error");
    if (wrap) {
      wrap.classList.add("has-error");
    }

    if (errorEl) {
      errorEl.textContent = message;
    }
  }

  function clearError(input) {
    const errorEl = getErrorElement(input);
    const wrap = getFieldWrap(input);

    input.classList.remove("input-error");
    if (wrap) {
      wrap.classList.remove("has-error");
    }

    if (errorEl) {
      errorEl.textContent = "";
    }
  }

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

  function startPageTransition(targetHref) {
    document.body.classList.add("page-exit");

    setTimeout(() => {
      window.location.href = targetHref;
    }, 260);
  }

  function validateRequired(input, message) {
    if (!input.value.trim()) {
      setError(input, message);
      return false;
    }
    clearError(input);
    return true;
  }

  function validateNIC() {
    const value = nic.value.trim();
    const nicPattern = /^(?:\d{9}[VvXx]|\d{12})$/;

    if (!value) {
      setError(nic, "NIC is required.");
      return false;
    }

    if (!nicPattern.test(value)) {
      setError(nic, "NIC must be 9 digits + V/X or 12 digits.");
      return false;
    }

    clearError(nic);
    return true;
  }

  function validatePhone() {
    const value = phone.value.trim();

    if (!value) {
      clearError(phone);
      return true;
    }

    if (!/^\d{10}$/.test(value)) {
      setError(phone, "Phone number must be exactly 10 digits.");
      return false;
    }

    clearError(phone);
    return true;
  }

  function validateEmail() {
    const value = email.value.trim();
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!value) {
      setError(email, "Email is required.");
      return false;
    }

    if (!emailPattern.test(value)) {
      setError(email, "Enter a valid email address.");
      return false;
    }

    clearError(email);
    return true;
  }

  function validatePassword() {
    const value = password.value;
    const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/;

    if (!value) {
      setError(password, "Password is required.");
      return false;
    }

    if (!passwordPattern.test(value)) {
      setError(
        password,
        "Password must be at least 8 characters and include uppercase, lowercase, number, and symbol."
      );
      return false;
    }

    clearError(password);
    return true;
  }

  function validateConfirmPassword() {
    const value = confirmPassword.value;

    if (!value) {
      setError(confirmPassword, "Please confirm your password.");
      return false;
    }

    if (value !== password.value) {
      setError(confirmPassword, "Passwords do not match.");
      return false;
    }

    clearError(confirmPassword);
    return true;
  }

  function getPasswordStrength(passwordValue) {
    let score = 0;
    if (passwordValue.length >= 8) score += 1;
    if (/[A-Z]/.test(passwordValue)) score += 1;
    if (/[a-z]/.test(passwordValue)) score += 1;
    if (/[0-9]/.test(passwordValue)) score += 1;
    if (/[^A-Za-z0-9]/.test(passwordValue)) score += 1;

    if (!passwordValue) return { label: "—", color: "#66758c" };
    if (score <= 2) return { label: "Weak", color: "#b26a00" };
    if (score <= 4) return { label: "Medium", color: "#1f7a46" };
    return { label: "Strong", color: "#1f7a46" };
  }

  function updatePasswordStrength() {
    if (!passwordStrengthText) return;
    const result = getPasswordStrength(password.value.trim());
    passwordStrengthText.textContent = `Password strength: ${result.label}`;
    passwordStrengthText.style.color = result.color;
  }

  function populateDOBFields() {
    const monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];

    monthNames.forEach((month, index) => {
      const option = document.createElement("option");
      option.value = String(index + 1).padStart(2, "0");
      option.textContent = month;
      dobMonth.appendChild(option);
    });

    for (let day = 1; day <= 31; day++) {
      const option = document.createElement("option");
      option.value = String(day).padStart(2, "0");
      option.textContent = day;
      dobDay.appendChild(option);
    }

    const currentYear = new Date().getFullYear();
    const startYear = currentYear - 100;
    const endYear = currentYear - 18;

    for (let year = endYear; year >= startYear; year--) {
      const option = document.createElement("option");
      option.value = String(year);
      option.textContent = year;
      dobYear.appendChild(option);
    }
  }

  function updateDayOptions() {
    const selectedMonth = parseInt(dobMonth.value, 10);
    const selectedYear = parseInt(dobYear.value, 10);
    const currentSelectedDay = dobDay.value;

    let daysInMonth = 31;

    if (selectedMonth && selectedYear) {
      daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
    } else if (selectedMonth) {
      const tempYear = 2000;
      daysInMonth = new Date(tempYear, selectedMonth, 0).getDate();
    }

    dobDay.innerHTML = '<option value="">Day</option>';

    for (let day = 1; day <= daysInMonth; day++) {
      const option = document.createElement("option");
      option.value = String(day).padStart(2, "0");
      option.textContent = day;
      if (String(day).padStart(2, "0") === currentSelectedDay) {
        option.selected = true;
      }
      dobDay.appendChild(option);
    }

    if (currentSelectedDay && parseInt(currentSelectedDay, 10) > daysInMonth) {
      dobDay.value = "";
    }
  }

  function syncDOBHiddenField() {
    const month = dobMonth.value;
    const day = dobDay.value;
    const year = dobYear.value;

    if (year && month && day) {
      dateOfBirth.value = `${year}-${month}-${day}`;
    } else {
      dateOfBirth.value = "";
    }
  }

  function clearDOBError() {
    dobMonth.classList.remove("input-error");
    dobDay.classList.remove("input-error");
    dobYear.classList.remove("input-error");

    const errorEl = dobYear.parentElement.parentElement.querySelector(".error-text");
    if (errorEl) {
      errorEl.textContent = "";
    }
  }

  function setDOBError(message) {
    dobMonth.classList.add("input-error");
    dobDay.classList.add("input-error");
    dobYear.classList.add("input-error");

    const errorEl = dobYear.parentElement.parentElement.querySelector(".error-text");
    if (errorEl) {
      errorEl.textContent = message;
    }
  }

  function validateDOB() {
    const month = dobMonth.value;
    const day = dobDay.value;
    const year = dobYear.value;

    const hasAnyValue = month || day || year;

    if (!hasAnyValue) {
      clearDOBError();
      return true;
    }

    if (!month || !day || !year) {
      setDOBError("Please select complete date of birth.");
      return false;
    }

    const selectedDate = new Date(`${year}-${month}-${day}T00:00:00`);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (Number.isNaN(selectedDate.getTime())) {
      setDOBError("Please select a valid date of birth.");
      return false;
    }

    if (selectedDate > today) {
      setDOBError("Date of birth cannot be in the future.");
      return false;
    }

    clearDOBError();
    return true;
  }

  function handleDOBChange() {
    updateDayOptions();
    syncDOBHiddenField();
    validateDOB();
  }

  populateDOBFields();
  updateDayOptions();
  updatePasswordStrength();

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

  nic.addEventListener("input", function () {
    let value = this.value.replace(/\s+/g, "").toUpperCase();
    value = value.replace(/[^0-9VX]/g, "");

    if (value.includes("V") || value.includes("X")) {
      const digits = value.replace(/[^0-9]/g, "").slice(0, 9);
      const letter = value.includes("V") ? "V" : "X";
      value = digits + letter;
    } else {
      value = value.replace(/[^0-9]/g, "").slice(0, 12);
    }

    this.value = value;

    if (this.value.length > 0) {
      validateNIC();
    } else {
      clearError(nic);
    }
  });

  phone.addEventListener("input", function () {
    this.value = this.value.replace(/\D/g, "").slice(0, 10);
    validatePhone();
  });

  firstName.addEventListener("blur", function () {
    validateRequired(firstName, "First name is required.");
  });

  lastName.addEventListener("blur", function () {
    validateRequired(lastName, "Last name is required.");
  });

  nic.addEventListener("blur", validateNIC);
  phone.addEventListener("blur", validatePhone);
  email.addEventListener("blur", validateEmail);
  password.addEventListener("blur", validatePassword);
  confirmPassword.addEventListener("blur", validateConfirmPassword);

  dobMonth.addEventListener("change", handleDOBChange);
  dobDay.addEventListener("change", handleDOBChange);
  dobYear.addEventListener("change", handleDOBChange);

  dobMonth.addEventListener("blur", validateDOB);
  dobDay.addEventListener("blur", validateDOB);
  dobYear.addEventListener("blur", validateDOB);

  password.addEventListener("input", function () {
    validatePassword();
    updatePasswordStrength();
    if (confirmPassword.value) {
      validateConfirmPassword();
    }
  });

  confirmPassword.addEventListener("input", validateConfirmPassword);

  form.addEventListener("submit", function (event) {
    syncDOBHiddenField();

    const isFirstNameValid = validateRequired(firstName, "First name is required.");
    const isLastNameValid = validateRequired(lastName, "Last name is required.");
    const isNICValid = validateNIC();
    const isPhoneValid = validatePhone();
    const isEmailValid = validateEmail();
    const isPasswordValid = validatePassword();
    const isConfirmPasswordValid = validateConfirmPassword();
    const isDOBValid = validateDOB();

    if (
      !isFirstNameValid ||
      !isLastNameValid ||
      !isNICValid ||
      !isPhoneValid ||
      !isEmailValid ||
      !isPasswordValid ||
      !isConfirmPasswordValid ||
      !isDOBValid
    ) {
      event.preventDefault();
      return;
    }

    if (registerSubmitBtn) {
      registerSubmitBtn.classList.add("loading");
      const btnText = registerSubmitBtn.querySelector(".btn-text");
      if (btnText) {
        btnText.textContent = "Creating account...";
      }
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "/" && document.activeElement !== firstName && firstName) {
      const tag = document.activeElement ? document.activeElement.tagName : "";
      if (tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") {
        event.preventDefault();
        firstName.focus();
      }
    }
  });

  document.querySelectorAll('a[href]').forEach((link) => {
    link.addEventListener("click", function (event) {
      const href = this.getAttribute("href");

      if (!href || href.startsWith("#") || this.target === "_blank") {
        return;
      }

      try {
        const targetUrl = new URL(href, window.location.href);

        if (targetUrl.origin !== window.location.origin) {
          return;
        }
      } catch (error) {
        return;
      }

      event.preventDefault();
      startPageTransition(href);
    });
  });
});