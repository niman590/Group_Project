document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("registerForm");

  const firstName = document.getElementById("first_name");
  const lastName = document.getElementById("last_name");
  const nic = document.getElementById("nic");
  const phone = document.getElementById("phone");
  const email = document.getElementById("email");
  const password = document.getElementById("password");
  const confirmPassword = document.getElementById("confirm_password");

  function getErrorElement(input) {
    return input.parentElement.querySelector(".error-text");
  }

  function setError(input, message) {
    const errorEl = getErrorElement(input);
    input.classList.add("input-error");
    if (errorEl) {
      errorEl.textContent = message;
    }
  }

  function clearError(input) {
    const errorEl = getErrorElement(input);
    input.classList.remove("input-error");
    if (errorEl) {
      errorEl.textContent = "";
    }
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

  password.addEventListener("input", function () {
    validatePassword();
    if (confirmPassword.value) {
      validateConfirmPassword();
    }
  });

  confirmPassword.addEventListener("input", validateConfirmPassword);

  form.addEventListener("submit", function (event) {
    const isFirstNameValid = validateRequired(firstName, "First name is required.");
    const isLastNameValid = validateRequired(lastName, "Last name is required.");
    const isNICValid = validateNIC();
    const isPhoneValid = validatePhone();
    const isEmailValid = validateEmail();
    const isPasswordValid = validatePassword();
    const isConfirmPasswordValid = validateConfirmPassword();

    if (
      !isFirstNameValid ||
      !isLastNameValid ||
      !isNICValid ||
      !isPhoneValid ||
      !isEmailValid ||
      !isPasswordValid ||
      !isConfirmPasswordValid
    ) {
      event.preventDefault();
    }
  });
});