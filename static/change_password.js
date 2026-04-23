document.addEventListener("DOMContentLoaded", function () {
    const newPasswordInput = document.getElementById("new_password");
    const confirmPasswordInput = document.getElementById("confirm_password");
    const strengthText = document.getElementById("passwordStrengthText");
    const toggleButtons = document.querySelectorAll(".toggle-password");

    function getPasswordStrength(password) {
        let score = 0;

        if (password.length >= 8) score++;
        if (/[a-z]/.test(password)) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/\d/.test(password)) score++;
        if (/[^\w\s]/.test(password)) score++;

        if (score <= 2) return "Weak";
        if (score <= 4) return "Medium";
        return "Strong";
    }

    if (newPasswordInput && strengthText) {
        newPasswordInput.addEventListener("input", function () {
            const password = this.value.trim();
            strengthText.textContent = password ? getPasswordStrength(password) : "—";
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

    if (confirmPasswordInput && newPasswordInput) {
        confirmPasswordInput.addEventListener("input", function () {
            if (this.value && newPasswordInput.value !== this.value) {
                this.style.borderColor = "#d64545";
            } else {
                this.style.borderColor = "";
            }
        });
    }
});