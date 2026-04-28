document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("passwordResetForm");

    const emailInput = document.getElementById("email");
    const otpInput = document.getElementById("otp");
    const newPasswordInput = document.getElementById("new_password");
    const confirmPasswordInput = document.getElementById("confirm_password");

    const sendOtpBtn = document.getElementById("sendOtpBtn");
    const verifyOtpBtn = document.getElementById("verifyOtpBtn");
    const resetPasswordBtn = document.getElementById("resetPasswordBtn");

    const strengthText = document.getElementById("passwordStrengthText");
    const toggleButtons = document.querySelectorAll(".toggle-password");

    const emailError = document.getElementById("emailError");
    const otpError = document.getElementById("otpError");
    const newPasswordError = document.getElementById("newPasswordError");
    const confirmPasswordError = document.getElementById("confirmPasswordError");

    let touched = {
        email: false,
        otp: false,
        new_password: false,
        confirm_password: false
    };

    let otpVerified = false;

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

    function showFlash(message, type = "error") {
        const oldBox = document.querySelector(".flash-messages.dynamic-flash");
        if (oldBox) oldBox.remove();

        const box = document.createElement("div");
        box.className = "flash-messages dynamic-flash";

        const item = document.createElement("div");
        item.className = `flash-message ${type}`;

        const inner = document.createElement("div");
        inner.className = "flash-inner";

        const icon = document.createElement("i");
        if (type === "success") {
            icon.className = "fa-solid fa-circle-check";
        } else if (type === "error") {
            icon.className = "fa-solid fa-circle-xmark";
        } else {
            icon.className = "fa-solid fa-circle-info";
        }

        const text = document.createElement("span");
        text.textContent = message;

        inner.appendChild(icon);
        inner.appendChild(text);
        item.appendChild(inner);
        box.appendChild(item);

        const sectionHeader = document.querySelector(".section-header");
        if (sectionHeader && sectionHeader.parentNode) {
            sectionHeader.parentNode.insertBefore(box, sectionHeader.nextSibling);
        }
    }

    function startPageTransition(targetHref) {
        document.body.classList.add("page-exit");

        setTimeout(() => {
            window.location.href = targetHref;
        }, 260);
    }

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email || "");
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

    function validateEmail(showError = false) {
        const value = emailInput.value.trim();

        if (!value) {
            if (showError) {
                setInputState(emailInput, emailError, "Recovery email is required.");
            } else {
                clearInputState(emailInput, emailError);
            }
            return false;
        }

        if (!isValidEmail(value)) {
            if (showError) {
                setInputState(emailInput, emailError, "Please enter a valid email address.");
            } else {
                clearInputState(emailInput, emailError);
            }
            return false;
        }

        setInputState(emailInput, emailError, "");
        return true;
    }

    function validateOtp(showError = false) {
        const value = otpInput.value.trim();

        if (!value) {
            if (showError) {
                setInputState(otpInput, otpError, "OTP is required.");
            } else {
                clearInputState(otpInput, otpError);
            }
            return false;
        }

        if (!/^\d{6}$/.test(value)) {
            if (showError) {
                setInputState(otpInput, otpError, "OTP must be exactly 6 digits.");
            } else {
                clearInputState(otpInput, otpError);
            }
            return false;
        }

        setInputState(otpInput, otpError, "");
        return true;
    }

    function validateNewPassword(showError = false) {
        const value = newPasswordInput.value.trim();

        if (!value) {
            if (showError) {
                setInputState(newPasswordInput, newPasswordError, "New password is required.");
            } else {
                clearInputState(newPasswordInput, newPasswordError);
            }
            return false;
        }

        if (!isStrongPassword(value)) {
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
        const emailOk = validateEmail(touched.email);
        const otpOk = validateOtp(touched.otp);
        const newOk = validateNewPassword(touched.new_password);
        const confirmOk = validateConfirmPassword(touched.confirm_password);

        if (resetPasswordBtn) {
            resetPasswordBtn.disabled = !(emailOk && otpOk && newOk && confirmOk && otpVerified);
        }
    }

    function setButtonBusy(button, busy, busyText, normalText) {
        if (!button) return;
        button.disabled = busy;
        button.textContent = busy ? busyText : normalText;
    }

    async function sendOtpRequest() {
        const response = await fetch("/send-otp", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: emailInput.value.trim()
            })
        });

        return await response.json();
    }

    async function verifyOtpRequest() {
        const response = await fetch("/verify-otp", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                otp: otpInput.value.trim()
            })
        });

        return await response.json();
    }

    async function resetPasswordRequest() {
        const response = await fetch("/reset-password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                new_password: newPasswordInput.value.trim()
            })
        });

        return await response.json();
    }

    if (emailInput) {
        emailInput.addEventListener("input", function () {
            touched.email = this.value.trim().length > 0;
            validateEmail(touched.email);
            otpVerified = false;
            updateSubmitState();
        });

        emailInput.addEventListener("blur", function () {
            touched.email = true;
            validateEmail(true);
            updateSubmitState();
        });
    }

    if (otpInput) {
        otpInput.addEventListener("input", function () {
            this.value = this.value.replace(/\D/g, "").slice(0, 6);
            touched.otp = this.value.trim().length > 0;
            validateOtp(touched.otp);
            otpVerified = false;
            updateSubmitState();
        });

        otpInput.addEventListener("blur", function () {
            touched.otp = true;
            validateOtp(true);
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

    if (sendOtpBtn) {
        sendOtpBtn.addEventListener("click", async function (event) {
            event.preventDefault();

            touched.email = true;

            if (!validateEmail(true)) {
                updateSubmitState();
                return;
            }

            setButtonBusy(sendOtpBtn, true, "Sending...", "Send OTP");

            try {
                const result = await sendOtpRequest();

                if (result.success) {
                    otpVerified = false;
                    showFlash(result.message || "OTP sent successfully.", "success");
                } else {
                    showFlash(result.message || "Failed to send OTP.", "error");
                }
            } catch (error) {
                showFlash("Something went wrong while sending OTP.", "error");
            } finally {
                setButtonBusy(sendOtpBtn, false, "Sending...", "Send OTP");
                updateSubmitState();
            }
        });
    }

    if (verifyOtpBtn) {
        verifyOtpBtn.addEventListener("click", async function (event) {
            event.preventDefault();

            touched.otp = true;

            const otpOk = validateOtp(true);
            if (!otpOk) {
                updateSubmitState();
                return;
            }

            setButtonBusy(verifyOtpBtn, true, "Verifying...", "Verify OTP");

            try {
                const result = await verifyOtpRequest();

                if (result.success) {
                    otpVerified = true;
                    clearInputState(otpInput, otpError);
                    showFlash(result.message || "OTP verified successfully.", "success");
                } else {
                    otpVerified = false;
                    setInputState(otpInput, otpError, result.message || "Invalid OTP.");
                    showFlash(result.message || "OTP verification failed.", "error");
                }
            } catch (error) {
                otpVerified = false;
                showFlash("Something went wrong while verifying OTP.", "error");
            } finally {
                setButtonBusy(verifyOtpBtn, false, "Verifying...", "Verify OTP");
                updateSubmitState();
            }
        });
    }

    if (resetPasswordBtn) {
        resetPasswordBtn.addEventListener("click", async function (event) {
            event.preventDefault();

            touched.email = true;
            touched.otp = true;
            touched.new_password = true;
            touched.confirm_password = true;

            const emailOk = validateEmail(true);
            const otpOk = validateOtp(true);
            const newOk = validateNewPassword(true);
            const confirmOk = validateConfirmPassword(true);

            if (!(emailOk && otpOk && newOk && confirmOk && otpVerified)) {
                if (!otpVerified) {
                    showFlash("Please verify your OTP before resetting the password.", "error");
                }
                updateSubmitState();
                return;
            }

            setButtonBusy(resetPasswordBtn, true, "Resetting...", "Reset Password");

            try {
                const result = await resetPasswordRequest();

                if (result.success) {
                    showFlash(result.message || "Password reset successfully.", "success");
                    otpVerified = false;
                    form.reset();
                    updateStrengthUI("");
                    touched = {
                        email: false,
                        otp: false,
                        new_password: false,
                        confirm_password: false
                    };
                    clearInputState(emailInput, emailError);
                    clearInputState(otpInput, otpError);
                    clearInputState(newPasswordInput, newPasswordError);
                    clearInputState(confirmPasswordInput, confirmPasswordError);

                    setTimeout(() => {
                        const backLink = document.querySelector(".back-text a");
                        if (backLink) {
                            window.location.href = backLink.getAttribute("href");
                        }
                    }, 1200);
                } else {
                    showFlash(result.message || "Password reset failed.", "error");
                }
            } catch (error) {
                showFlash("Something went wrong while resetting the password.", "error");
            } finally {
                setButtonBusy(resetPasswordBtn, false, "Resetting...", "Reset Password");
                updateSubmitState();
            }
        });
    }

    if (form) {
        form.addEventListener("submit", function (event) {
            event.preventDefault();
        });
    }

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

    updateStrengthUI("");
    clearInputState(emailInput, emailError);
    clearInputState(otpInput, otpError);
    clearInputState(newPasswordInput, newPasswordError);
    clearInputState(confirmPasswordInput, confirmPasswordError);

    if (resetPasswordBtn) {
        resetPasswordBtn.disabled = true;
    }
});