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

  const passwordStrengthBox = document.getElementById("passwordStrengthBox");
  const passwordStrengthText = document.getElementById("passwordStrengthText");
  const passwordStrengthFill = document.getElementById("passwordStrengthFill");
  const passwordPolicyError = document.getElementById("passwordPolicyError");

  const flashMessages = document.querySelectorAll("[data-flash]");
  const flashCloseButtons = document.querySelectorAll("[data-flash-close]");
  const passwordToggles = document.querySelectorAll(".password-toggle");

  const defaultCommonRuleText = "Not common, personal, or breached";

  const commonPasswords = new Set([
    "password",
    "password123",
    "password@123",
    "admin123",
    "admin@123",
    "123456",
    "12345678",
    "123456789",
    "qwerty",
    "qwerty123",
    "letmein",
    "welcome",
    "welcome123",
    "iloveyou",
    "abc123",
    "111111",
    "000000",
    "civicplan123",
    "civicplan@123"
  ]);

  const passwordRules = {
    length: document.getElementById("ruleLength"),
    upper: document.getElementById("ruleUpper"),
    lower: document.getElementById("ruleLower"),
    number: document.getElementById("ruleNumber"),
    symbol: document.getElementById("ruleSymbol"),
    common: document.getElementById("ruleCommon")
  };

  function isCommonPassword(passwordValue) {
    return commonPasswords.has((passwordValue || "").trim().toLowerCase());
  }

  function containsPersonalInfo(passwordValue) {
    const normalizedPassword = (passwordValue || "")
      .trim()
      .toLowerCase()
      .replace(/[\s._-]/g, "");

    if (!normalizedPassword) {
      return false;
    }

    const personalValues = [
      firstName ? firstName.value : "",
      lastName ? lastName.value : "",
      nic ? nic.value : "",
      phone ? phone.value : "",
      email ? email.value : "",
      city ? city.value : ""
    ];

    for (const value of personalValues) {
      if (!value) continue;

      const normalizedValue = String(value)
        .trim()
        .toLowerCase();

      if (!normalizedValue) continue;

      const emailName = normalizedValue.includes("@")
        ? normalizedValue.split("@")[0]
        : normalizedValue;

      const variants = [
        normalizedValue,
        emailName,
        normalizedValue.replace(/[\s._-]/g, ""),
        emailName.replace(/[\s._-]/g, "")
      ];

      for (const item of variants) {
        if (item.length >= 3 && normalizedPassword.includes(item)) {
          return true;
        }
      }
    }

    return false;
  }

  function getPasswordPolicyMessage() {
    const value = password.value;
    const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/;

    if (!value) {
      return "Password is required.";
    }

    if (!passwordPattern.test(value)) {
      return "Password must be at least 8 characters and include uppercase, lowercase, number, and symbol.";
    }

    if (isCommonPassword(value)) {
      return "This password is too common. Please choose a more secure password.";
    }

    if (containsPersonalInfo(value)) {
      return "Password must not contain your name, email, NIC, phone number, or city.";
    }

    return "";
  }

  function getRuleTextElement(ruleElement) {
    if (!ruleElement) {
      return null;
    }

    return ruleElement.querySelector("span");
  }

  function setCommonRuleMessage(message) {
    const ruleText = getRuleTextElement(passwordRules.common);

    if (ruleText) {
      ruleText.textContent = message || defaultCommonRuleText;
    }
  }

  function setPasswordBoxWeakFromServerError() {
    if (!passwordStrengthBox || !passwordStrengthText || !passwordStrengthFill) {
      return;
    }

    passwordStrengthBox.classList.remove("fair", "good", "strong");
    passwordStrengthBox.classList.add("active", "weak");

    passwordStrengthText.textContent = "Weak";
    passwordStrengthFill.style.width = "25%";
  }

  function applyServerPasswordPolicyError() {
    const serverError = (window.serverPasswordPolicyError || "").trim();

    if (!serverError || !passwordRules.common) {
      return;
    }

    const lowerError = serverError.toLowerCase();

    const shouldShowInCommonRule =
      lowerError.includes("common") ||
      lowerError.includes("breach") ||
      lowerError.includes("breached") ||
      lowerError.includes("name") ||
      lowerError.includes("email") ||
      lowerError.includes("nic") ||
      lowerError.includes("phone") ||
      lowerError.includes("city") ||
      lowerError.includes("personal");

    if (!shouldShowInCommonRule) {
      return;
    }

    const icon = passwordRules.common.querySelector("i");

    passwordRules.common.classList.remove("valid");

    if (icon) {
      icon.className = "fa-solid fa-xmark";
    }

    setCommonRuleMessage("Too common, personal, or breached");
    setPasswordBoxWeakFromServerError();
  }

  function clearServerPasswordPolicyError() {
    window.serverPasswordPolicyError = "";
    setCommonRuleMessage(defaultCommonRuleText);

    if (passwordPolicyError) {
      passwordPolicyError.textContent = "";
    }
  }

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

  function validatePassword(showError = false) {
    const message = getPasswordPolicyMessage();

    if (message) {
      clearError(password);

      if (showError && passwordPolicyError) {
        passwordPolicyError.textContent = message;
      }

      return false;
    }

    clearError(password);

    if (passwordPolicyError) {
      passwordPolicyError.textContent = "";
    }

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

  function getPasswordChecks(passwordValue) {
    const commonOk =
      passwordValue.length > 0 &&
      !isCommonPassword(passwordValue) &&
      !containsPersonalInfo(passwordValue);

    return {
      length: passwordValue.length >= 8,
      upper: /[A-Z]/.test(passwordValue),
      lower: /[a-z]/.test(passwordValue),
      number: /\d/.test(passwordValue),
      symbol: /[^\w\s]/.test(passwordValue),
      common: commonOk
    };
  }

  function updatePasswordRule(ruleElement, isValid) {
    if (!ruleElement) {
      return;
    }

    const icon = ruleElement.querySelector("i");

    if (isValid) {
      ruleElement.classList.add("valid");

      if (icon) {
        icon.className = "fa-solid fa-check";
      }
    } else {
      ruleElement.classList.remove("valid");

      if (icon) {
        icon.className = "fa-solid fa-xmark";
      }
    }
  }

  function updatePasswordStrength() {
    if (!passwordStrengthBox || !passwordStrengthText || !passwordStrengthFill) {
      return;
    }

    const passwordValue = password.value;
    const checks = getPasswordChecks(passwordValue);
    const score = Object.values(checks).filter(Boolean).length;

    setCommonRuleMessage(defaultCommonRuleText);

    updatePasswordRule(passwordRules.length, checks.length);
    updatePasswordRule(passwordRules.upper, checks.upper);
    updatePasswordRule(passwordRules.lower, checks.lower);
    updatePasswordRule(passwordRules.number, checks.number);
    updatePasswordRule(passwordRules.symbol, checks.symbol);
    updatePasswordRule(passwordRules.common, checks.common);

    passwordStrengthBox.classList.remove("active", "weak", "fair", "good", "strong");

    if (!passwordValue) {
      passwordStrengthText.textContent = "Not started";
      passwordStrengthFill.style.width = "0%";
      return;
    }

    passwordStrengthBox.classList.add("active");

    if (score <= 2) {
      passwordStrengthBox.classList.add("weak");
      passwordStrengthText.textContent = "Weak";
      passwordStrengthFill.style.width = "25%";
    } else if (score === 3) {
      passwordStrengthBox.classList.add("fair");
      passwordStrengthText.textContent = "Fair";
      passwordStrengthFill.style.width = "50%";
    } else if (score === 4) {
      passwordStrengthBox.classList.add("good");
      passwordStrengthText.textContent = "Good";
      passwordStrengthFill.style.width = "75%";
    } else if (score === 5) {
      passwordStrengthBox.classList.add("good");
      passwordStrengthText.textContent = "Good";
      passwordStrengthFill.style.width = "90%";
    } else {
      passwordStrengthBox.classList.add("strong");
      passwordStrengthText.textContent = "Strong";
      passwordStrengthFill.style.width = "100%";
    }
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

  function restoreDOBFromHiddenField() {
    const savedDate = dateOfBirth.value || window.prefilledDateOfBirth || "";

    if (!savedDate || !/^\d{4}-\d{2}-\d{2}$/.test(savedDate)) {
      return;
    }

    const parts = savedDate.split("-");
    const year = parts[0];
    const month = parts[1];
    const day = parts[2];

    dobYear.value = year;
    dobMonth.value = month;
    updateDayOptions();
    dobDay.value = day;
    syncDOBHiddenField();
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
  restoreDOBFromHiddenField();
  updatePasswordStrength();
  applyServerPasswordPolicyError();

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

  [firstName, lastName, nic, phone, email, city].forEach((input) => {
    if (!input) return;

    input.addEventListener("input", function () {
      if (password.value) {
        validatePassword();
        updatePasswordStrength();
      }
    });
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
    clearServerPasswordPolicyError();
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
    const isPasswordValid = validatePassword(true);
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

      if (!isPasswordValid) {
        password.focus();
      }

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

  document.querySelectorAll("a[href]").forEach((link) => {
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