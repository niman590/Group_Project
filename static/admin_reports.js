document.addEventListener("DOMContentLoaded", function () {
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

    const viewAllButtons = document.querySelectorAll(".view-all-btn");

    viewAllButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const targetClass = this.getAttribute("data-target");
            const hiddenRows = document.querySelectorAll("." + targetClass + ".extra-row");
            const isExpanded = this.getAttribute("data-expanded") === "true";

            hiddenRows.forEach(function (row) {
                row.classList.toggle("hidden-row", isExpanded);
            });

            this.setAttribute("data-expanded", isExpanded ? "false" : "true");
            this.textContent = isExpanded ? "View All" : "Show Less";
        });
    });
});