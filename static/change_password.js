document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("changePasswordForm");
    const currentPasswordInput = document.getElementById("current_password");
    const newPasswordInput = document.getElementById("new_password");
    const confirmPasswordInput = document.getElementById("confirm_password");
    const changePasswordBtn = document.getElementById("changePasswordBtn");

    const strengthBox = document.getElementById("passwordStrengthBox");
    const strengthText = document.getElementById("passwordStrengthText");
    const strengthFill = document.getElementById("passwordStrengthFill");

    const toggleButtons = document.querySelectorAll(".toggle-password");

    const currentPasswordError = document.getElementById("currentPasswordError");
    const newPasswordError = document.getElementById("newPasswordError");
    const confirmPasswordError = document.getElementById("confirmPasswordError");

    const passwordRules = {
        length: document.getElementById("ruleLength"),
        upper: document.getElementById("ruleUpper"),
        lower: document.getElementById("ruleLower"),
        number: document.getElementById("ruleNumber"),
        symbol: document.getElementById("ruleSymbol")
    };

    let touched = {
        current_password: false,
        new_password: false,
        confirm_password: false
    };

    function setInputState(input, errorElement, message) {
        if (!input) return;

        const wrapper = input.closest(".input-wrap");

        if (message) {
            if (wrapper) wrapper.classList.add("invalid");
            if (errorElement) errorElement.textContent = message;
        } else {
            if (wrapper) wrapper.classList.remove("invalid");
            if (errorElement) errorElement.textContent = "";
        }
    }

    function clearInputState(input, errorElement) {
        if (!input) return;

        const wrapper = input.closest(".input-wrap");

        if (wrapper) wrapper.classList.remove("invalid");
        if (errorElement) errorElement.textContent = "";
    }

    function isStrongPassword(password) {
        return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/.test(password || "");
    }

    function getPasswordChecks(password) {
        return {
            length: password.length >= 8,
            upper: /[A-Z]/.test(password),
            lower: /[a-z]/.test(password),
            number: /\d/.test(password),
            symbol: /[^\w\s]/.test(password)
        };
    }

    function updatePasswordRule(ruleElement, isValid) {
        if (!ruleElement) return;

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

    function updateStrengthUI(password) {
        if (!strengthBox || !strengthText || !strengthFill) {
            return;
        }

        const checks = getPasswordChecks(password);
        const score = Object.values(checks).filter(Boolean).length;

        updatePasswordRule(passwordRules.length, checks.length);
        updatePasswordRule(passwordRules.upper, checks.upper);
        updatePasswordRule(passwordRules.lower, checks.lower);
        updatePasswordRule(passwordRules.number, checks.number);
        updatePasswordRule(passwordRules.symbol, checks.symbol);

        strengthBox.classList.remove("active", "weak", "fair", "good", "strong");

        if (!password) {
            strengthText.textContent = "Not started";
            strengthFill.style.width = "0%";
            return;
        }

        strengthBox.classList.add("active");

        if (score <= 2) {
            strengthBox.classList.add("weak");
            strengthText.textContent = "Weak";
            strengthFill.style.width = "25%";
        } else if (score === 3) {
            strengthBox.classList.add("fair");
            strengthText.textContent = "Fair";
            strengthFill.style.width = "50%";
        } else if (score === 4) {
            strengthBox.classList.add("good");
            strengthText.textContent = "Good";
            strengthFill.style.width = "75%";
        } else {
            strengthBox.classList.add("strong");
            strengthText.textContent = "Strong";
            strengthFill.style.width = "100%";
        }
    }

    function validateCurrentPassword(showError = false) {
        const value = currentPasswordInput.value.trim();

        if (!value) {
            if (showError) {
                setInputState(currentPasswordInput, currentPasswordError, "Current password is required.");
            } else {
                clearInputState(currentPasswordInput, currentPasswordError);
            }

            return false;
        }

        setInputState(currentPasswordInput, currentPasswordError, "");
        return true;
    }

    function validateNewPassword(showError = false) {
        const currentValue = currentPasswordInput.value.trim();
        const newValue = newPasswordInput.value.trim();

        if (!newValue) {
            clearInputState(newPasswordInput, newPasswordError);
            return false;
        }

        if (!isStrongPassword(newValue)) {
            clearInputState(newPasswordInput, newPasswordError);
            return false;
        }

        if (currentValue && newValue === currentValue) {
            if (showError) {
                setInputState(
                    newPasswordInput,
                    newPasswordError,
                    "New password must be different from your current password."
                );
            } else {
                clearInputState(newPasswordInput, newPasswordError);
            }

            return false;
        }

        setInputState(newPasswordInput, newPasswordError, "");
        return true;
    }

    function validateConfirmPassword(showError = false) {
        const newValue = newPasswordInput.value.trim();
        const confirmValue = confirmPasswordInput.value.trim();

        if (!confirmValue) {
            if (showError) {
                setInputState(confirmPasswordInput, confirmPasswordError, "Please confirm your new password.");
            } else {
                clearInputState(confirmPasswordInput, confirmPasswordError);
            }

            return false;
        }

        if (newValue !== confirmValue) {
            if (showError) {
                setInputState(confirmPasswordInput, confirmPasswordError, "New password and confirm password do not match.");
            } else {
                clearInputState(confirmPasswordInput, confirmPasswordError);
            }

            return false;
        }

        setInputState(confirmPasswordInput, confirmPasswordError, "");
        return true;
    }

    function updateSubmitState() {
        const currentOk = validateCurrentPassword(touched.current_password);
        const newOk = validateNewPassword(touched.new_password);
        const confirmOk = validateConfirmPassword(touched.confirm_password);

        if (changePasswordBtn) {
            changePasswordBtn.disabled = !(currentOk && newOk && confirmOk);
        }
    }

    if (currentPasswordInput) {
        currentPasswordInput.addEventListener("input", function () {
            touched.current_password = this.value.trim().length > 0;
            validateCurrentPassword(touched.current_password);

            if (touched.new_password) {
                validateNewPassword(true);
            }

            if (touched.confirm_password) {
                validateConfirmPassword(true);
            }

            updateSubmitState();
        });

        currentPasswordInput.addEventListener("blur", function () {
            touched.current_password = true;
            validateCurrentPassword(true);
            updateSubmitState();
        });
    }

    if (newPasswordInput) {
        newPasswordInput.addEventListener("input", function () {
            const value = this.value.trim();
            touched.new_password = value.length > 0;

            updateStrengthUI(value);
            validateNewPassword(touched.new_password);

            if (touched.confirm_password) {
                validateConfirmPassword(true);
            }

            updateSubmitState();
        });

        newPasswordInput.addEventListener("blur", function () {
            touched.new_password = true;
            validateNewPassword(true);
            updateSubmitState();
        });
    }

    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener("input", function () {
            touched.confirm_password = this.value.trim().length > 0;
            validateConfirmPassword(touched.confirm_password);
            updateSubmitState();
        });

        confirmPasswordInput.addEventListener("blur", function () {
            touched.confirm_password = true;
            validateConfirmPassword(true);
            updateSubmitState();
        });
    }

    toggleButtons.forEach((button) => {
        button.addEventListener("click", function () {
            const targetId = this.getAttribute("data-target");
            const targetInput = document.getElementById(targetId);
            const icon = this.querySelector("i");

            if (!targetInput) return;

            if (targetInput.type === "password") {
                targetInput.type = "text";

                if (icon) {
                    icon.classList.remove("fa-eye");
                    icon.classList.add("fa-eye-slash");
                }
            } else {
                targetInput.type = "password";

                if (icon) {
                    icon.classList.remove("fa-eye-slash");
                    icon.classList.add("fa-eye");
                }
            }
        });
    });

    if (form) {
        form.addEventListener("submit", function (event) {
            touched.current_password = true;
            touched.new_password = true;
            touched.confirm_password = true;

            const currentOk = validateCurrentPassword(true);
            const newOk = validateNewPassword(true);
            const confirmOk = validateConfirmPassword(true);

            if (!(currentOk && newOk && confirmOk)) {
                event.preventDefault();
                updateSubmitState();

                if (!newOk) {
                    newPasswordInput.focus();
                }

                return;
            }
        });
    }

    updateStrengthUI("");
    clearInputState(currentPasswordInput, currentPasswordError);
    clearInputState(newPasswordInput, newPasswordError);
    clearInputState(confirmPasswordInput, confirmPasswordError);

    if (changePasswordBtn) {
        changePasswordBtn.disabled = true;
    }
});