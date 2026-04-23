document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("changePasswordForm");
    const currentPasswordInput = document.getElementById("current_password");
    const newPasswordInput = document.getElementById("new_password");
    const confirmPasswordInput = document.getElementById("confirm_password");
    const changePasswordBtn = document.getElementById("changePasswordBtn");
    const strengthText = document.getElementById("passwordStrengthText");
    const toggleButtons = document.querySelectorAll(".toggle-password");

    const currentPasswordError = document.getElementById("currentPasswordError");
    const newPasswordError = document.getElementById("newPasswordError");
    const confirmPasswordError = document.getElementById("confirmPasswordError");

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

    function getPasswordStrength(password) {
        let score = 0;

        if (password.length >= 8) score++;
        if (/[a-z]/.test(password)) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/\d/.test(password)) score++;
        if (/[^\w\s]/.test(password)) score++;

        if (password.length === 0) return "—";
        if (score <= 2) return "Weak";
        if (score <= 4) return "Medium";
        return "Strong";
    }

    function updateStrengthUI(password) {
        const strength = getPasswordStrength(password);

        strengthText.classList.remove("password-weak", "password-medium", "password-strong");
        strengthText.textContent = strength;

        if (strength === "Weak") {
            strengthText.classList.add("password-weak");
        } else if (strength === "Medium") {
            strengthText.classList.add("password-medium");
        } else if (strength === "Strong") {
            strengthText.classList.add("password-strong");
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
            if (showError) {
                setInputState(newPasswordInput, newPasswordError, "New password is required.");
            } else {
                clearInputState(newPasswordInput, newPasswordError);
            }
            return false;
        }

        if (!isStrongPassword(newValue)) {
            if (showError) {
                setInputState(
                    newPasswordInput,
                    newPasswordError,
                    "Password must be at least 8 characters and include uppercase, lowercase, number, and symbol."
                );
            } else {
                clearInputState(newPasswordInput, newPasswordError);
            }
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