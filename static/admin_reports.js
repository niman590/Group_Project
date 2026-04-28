document.addEventListener("DOMContentLoaded", function () {
    function pad2(value) {
        return String(value).padStart(2, "0");
    }

    function getTodayOnly() {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return today;
    }

    function isValidDateParts(year, month, day) {
        if (!year || !month || !day) return false;

        const numericYear = Number(year);
        const numericMonth = Number(month);
        const numericDay = Number(day);

        const date = new Date(numericYear, numericMonth - 1, numericDay);

        return (
            date.getFullYear() === numericYear &&
            date.getMonth() === numericMonth - 1 &&
            date.getDate() === numericDay
        );
    }

    function isFutureDate(year, month, day) {
        const selectedDate = new Date(Number(year), Number(month) - 1, Number(day));
        selectedDate.setHours(0, 0, 0, 0);
        return selectedDate > getTodayOnly();
    }

    function updateHiddenDate(row) {
        const targetId = row.getAttribute("data-date-target");
        const hiddenInput = document.getElementById(targetId);

        if (!hiddenInput) return;

        const monthSelect = row.querySelector('[data-date-part="month"]');
        const daySelect = row.querySelector('[data-date-part="day"]');
        const yearSelect = row.querySelector('[data-date-part="year"]');

        const month = monthSelect ? monthSelect.value : "";
        const day = daySelect ? daySelect.value : "";
        const year = yearSelect ? yearSelect.value : "";

        row.querySelectorAll(".report-date-select").forEach(function (select) {
            select.classList.remove("invalid");
        });

        if (!month && !day && !year) {
            hiddenInput.value = "";
            return;
        }

        if (isValidDateParts(year, month, day) && !isFutureDate(year, month, day)) {
            hiddenInput.value = year + "-" + pad2(month) + "-" + pad2(day);
            return;
        }

        hiddenInput.value = "";

        row.querySelectorAll(".report-date-select").forEach(function (select) {
            select.classList.add("invalid");
        });
    }

    function setDateSelectsFromHiddenValue(row) {
        const targetId = row.getAttribute("data-date-target");
        const hiddenInput = document.getElementById(targetId);

        if (!hiddenInput || !hiddenInput.value) return;

        const parts = hiddenInput.value.split("-");
        if (parts.length !== 3) return;

        const year = parts[0];
        const month = parts[1];
        const day = parts[2];

        const monthSelect = row.querySelector('[data-date-part="month"]');
        const daySelect = row.querySelector('[data-date-part="day"]');
        const yearSelect = row.querySelector('[data-date-part="year"]');

        if (monthSelect) monthSelect.value = month;
        if (daySelect) daySelect.value = day;
        if (yearSelect) yearSelect.value = year;
    }

    const dateRows = document.querySelectorAll(".report-date-select-row");

    dateRows.forEach(function (row) {
        setDateSelectsFromHiddenValue(row);
        updateHiddenDate(row);

        row.querySelectorAll(".report-date-select").forEach(function (select) {
            select.addEventListener("change", function () {
                updateHiddenDate(row);
            });
        });
    });

    const filterForms = document.querySelectorAll(".inline-filter-form");

    filterForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            let hasInvalidDate = false;

            const rows = form.querySelectorAll(".report-date-select-row");

            rows.forEach(function (row) {
                updateHiddenDate(row);

                const selects = row.querySelectorAll(".report-date-select");
                const values = Array.from(selects).map(function (select) {
                    return select.value;
                });

                const hasAnyValue = values.some(Boolean);
                const hasAllValues = values.every(Boolean);

                if (hasAnyValue && !hasAllValues) {
                    hasInvalidDate = true;
                    selects.forEach(function (select) {
                        select.classList.add("invalid");
                    });
                }

                if (hasAllValues && row.querySelector(".report-date-select.invalid")) {
                    hasInvalidDate = true;
                }
            });

            if (hasInvalidDate) {
                event.preventDefault();
            }
        });
    });

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