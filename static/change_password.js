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

    let touched = {
        current_password: false,
        new_password: false,
        confirm_password: false
    };

    function isCommonPassword(password) {
        return commonPasswords.has((password || "").trim().toLowerCase());
    }

    function containsPersonalInfo(passwordValue) {
        const normalizedPassword = (passwordValue || "")
            .trim()
            .toLowerCase()
            .replace(/[\s._-]/g, "");

        if (!normalizedPassword) {
            return false;
        }

        const profile = window.currentUserPasswordProfile || {};

        const personalValues = [
            profile.firstName || "",
            profile.lastName || "",
            profile.email || "",
            profile.nic || "",
            profile.phone || "",
            profile.city || ""
        ];

        for (const value of personalValues) {
            if (!value) continue;

            const normalizedValue = String(value).trim().toLowerCase();

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

    function clearServerPasswordPolicyError() {
        const serverError = document.querySelector(".password-policy-server-error");

        if (serverError) {
            serverError.textContent = "";
        }
    }

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
        return (
            /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/.test(password || "") &&
            !isCommonPassword(password) &&
            !containsPersonalInfo(password)
        );
    }

    function getPasswordChecks(password) {
        return {
            length: password.length >= 8,
            upper: /[A-Z]/.test(password),
            lower: /[a-z]/.test(password),
            number: /\d/.test(password),
            symbol: /[^\w\s]/.test(password),
            common: password.length > 0 &&
                    !isCommonPassword(password) &&
                    !containsPersonalInfo(password)
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

        const checks = getPasswordChecks(password || "");
        const score = Object.values(checks).filter(Boolean).length;

        updatePasswordRule(passwordRules.length, checks.length);
        updatePasswordRule(passwordRules.upper, checks.upper);
        updatePasswordRule(passwordRules.lower, checks.lower);
        updatePasswordRule(passwordRules.number, checks.number);
        updatePasswordRule(passwordRules.symbol, checks.symbol);
        updatePasswordRule(passwordRules.common, checks.common);

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
        } else if (score === 5) {
            strengthBox.classList.add("good");
            strengthText.textContent = "Good";
            strengthFill.style.width = "90%";
        } else {
            strengthBox.classList.add("strong");
            strengthText.textContent = "Strong";
            strengthFill.style.width = "100%";
        }
    }

    function getNewPasswordPolicyMessage() {
        if (!newPasswordInput) {
            return "New password is required.";
        }

        const value = newPasswordInput.value.trim();
        const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$/;

        if (!value) {
            return "New password is required.";
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

    function validateCurrentPassword(showError = false) {
        if (!currentPasswordInput) return false;

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
        if (!newPasswordInput || !currentPasswordInput) return false;

        const currentValue = currentPasswordInput.value.trim();
        const newValue = newPasswordInput.value.trim();

        const policyMessage = getNewPasswordPolicyMessage();

        if (policyMessage) {
            if (showError) {
                setInputState(newPasswordInput, newPasswordError, policyMessage);
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
        if (!newPasswordInput || !confirmPasswordInput) return false;

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

            clearServerPasswordPolicyError();
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

                if (!newOk && newPasswordInput) {
                    newPasswordInput.focus();
                } else if (!currentOk && currentPasswordInput) {
                    currentPasswordInput.focus();
                } else if (!confirmOk && confirmPasswordInput) {
                    confirmPasswordInput.focus();
                }
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