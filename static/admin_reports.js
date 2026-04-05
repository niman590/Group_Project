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
            this.textContent = targetElement.classList.contains("show") ? "Hide Details" : "View Details";
        });
    });

    const today = new Date();
    const calendarInputs = document.querySelectorAll(".js-friendly-calendar");

    if (window.flatpickr) {
        calendarInputs.forEach(function (input) {
            flatpickr(input, {
                dateFormat: "Y-m-d",
                altInput: true,
                altFormat: "F j, Y",
                allowInput: false,
                maxDate: today,
            });
        });
    } else {
        calendarInputs.forEach(function (input) {
            input.setAttribute("type", "date");
            input.setAttribute("max", today.toISOString().split("T")[0]);
        });
    }
});