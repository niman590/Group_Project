document.addEventListener("DOMContentLoaded", function () {
    const toggleButtons = document.querySelectorAll(".report-toggle-btn");

    toggleButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const targetId = this.getAttribute("data-target");
            const targetElement = document.getElementById(targetId);

            if (!targetElement) {
                return;
            }

            targetElement.classList.toggle("show");

            if (targetElement.classList.contains("show")) {
                this.textContent = "Hide Details";
            } else {
                this.textContent = "View Details";
            }
        });
    });
});