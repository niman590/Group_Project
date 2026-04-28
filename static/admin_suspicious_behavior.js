document.addEventListener("DOMContentLoaded", function () {
    const flashStack = document.getElementById("securityFlashStack");
    if (flashStack) {
        setTimeout(() => {
            flashStack.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            flashStack.style.opacity = "0";
            flashStack.style.transform = "translateY(-8px)";

            setTimeout(() => {
                flashStack.remove();
            }, 400);
        }, 3000);
    }

    const confirmOverlay = document.getElementById("systemConfirmOverlay");
    const confirmModal = confirmOverlay ? confirmOverlay.querySelector(".system-modal") : null;
    const confirmTitle = document.getElementById("systemConfirmTitle");
    const confirmMessage = document.getElementById("systemConfirmMessage");
    const confirmDetail = document.getElementById("systemConfirmDetail");
    const confirmIcon = document.getElementById("systemConfirmIcon");
    const confirmCancel = document.getElementById("systemConfirmCancel");
    const confirmProceed = document.getElementById("systemConfirmProceed");

    let activeForm = null;
    let allowSubmit = false;

    function openSystemConfirm(form) {
        activeForm = form;

        confirmTitle.textContent = form.dataset.confirmTitle || "Confirm Action";
        confirmMessage.textContent = form.dataset.confirmMessage || "Are you sure you want to continue?";
        confirmDetail.textContent = form.dataset.confirmDetail || "This action may update system records.";
        confirmProceed.textContent = form.dataset.confirmButton || "Confirm";

        const iconClass = form.dataset.confirmIcon || "fa-shield-halved";
        confirmIcon.className = "fa-solid " + iconClass;

        confirmOverlay.classList.add("is-visible");
        confirmOverlay.setAttribute("aria-hidden", "false");

        setTimeout(() => {
            confirmCancel.focus();
        }, 80);
    }

    function closeSystemConfirm() {
        confirmOverlay.classList.remove("is-visible");
        confirmOverlay.setAttribute("aria-hidden", "true");
        activeForm = null;
        allowSubmit = false;
        confirmProceed.disabled = false;
    }

    if (confirmOverlay && confirmCancel && confirmProceed) {
        document.querySelectorAll("[data-confirm-form]").forEach((form) => {
            form.addEventListener("submit", function (event) {
                if (allowSubmit) return;

                event.preventDefault();
                openSystemConfirm(form);
            });
        });

        confirmCancel.addEventListener("click", closeSystemConfirm);

        confirmProceed.addEventListener("click", function () {
            if (!activeForm) return;

            allowSubmit = true;
            confirmProceed.disabled = true;
            confirmProceed.textContent = "Processing...";

            activeForm.submit();
        });

        confirmOverlay.addEventListener("click", function (event) {
            if (event.target === confirmOverlay) {
                closeSystemConfirm();
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && confirmOverlay.classList.contains("is-visible")) {
                closeSystemConfirm();
            }
        });

        if (confirmModal) {
            confirmModal.addEventListener("click", function (event) {
                event.stopPropagation();
            });
        }
    }

    function splitDateToDropdowns(dateValue, monthId, dayId, yearId) {
        if (!dateValue) return;

        const parts = dateValue.split("-");
        if (parts.length !== 3) return;

        const yearElement = document.getElementById(yearId);
        const monthElement = document.getElementById(monthId);
        const dayElement = document.getElementById(dayId);

        if (!yearElement || !monthElement || !dayElement) return;

        yearElement.value = parts[0];
        monthElement.value = parts[1];
        dayElement.value = parts[2];
    }

    function updateHiddenDate(monthId, dayId, yearId, hiddenId) {
        const monthElement = document.getElementById(monthId);
        const dayElement = document.getElementById(dayId);
        const yearElement = document.getElementById(yearId);
        const hiddenInput = document.getElementById(hiddenId);

        if (!monthElement || !dayElement || !yearElement || !hiddenInput) return;

        const month = monthElement.value;
        const day = dayElement.value;
        const year = yearElement.value;

        if (month && day && year) {
            hiddenInput.value = `${year}-${month}-${day}`;
        } else {
            hiddenInput.value = "";
        }
    }

    const dates = window.securityFilterDates || {
        startDate: "",
        endDate: ""
    };

    splitDateToDropdowns(dates.startDate, "start_month", "start_day", "start_year");
    splitDateToDropdowns(dates.endDate, "end_month", "end_day", "end_year");

    ["start_month", "start_day", "start_year"].forEach((id) => {
        const element = document.getElementById(id);
        if (!element) return;

        element.addEventListener("change", function () {
            updateHiddenDate("start_month", "start_day", "start_year", "start_date");
        });
    });

    ["end_month", "end_day", "end_year"].forEach((id) => {
        const element = document.getElementById(id);
        if (!element) return;

        element.addEventListener("change", function () {
            updateHiddenDate("end_month", "end_day", "end_year", "end_date");
        });
    });

    const selectAllSecurityEvents = document.getElementById("selectAllSecurityEvents");
    const securityDownloadForm = document.getElementById("securityDownloadForm");

    if (selectAllSecurityEvents) {
        selectAllSecurityEvents.addEventListener("change", function () {
            document.querySelectorAll(".event-download-check").forEach((checkbox) => {
                checkbox.checked = selectAllSecurityEvents.checked;
            });
        });
    }

    document.querySelectorAll(".event-download-check").forEach((checkbox) => {
        checkbox.addEventListener("change", function () {
            const allChecks = document.querySelectorAll(".event-download-check");
            const checkedChecks = document.querySelectorAll(".event-download-check:checked");

            if (selectAllSecurityEvents) {
                selectAllSecurityEvents.checked = allChecks.length > 0 && checkedChecks.length === allChecks.length;
                selectAllSecurityEvents.indeterminate = checkedChecks.length > 0 && checkedChecks.length < allChecks.length;
            }
        });
    });

    if (securityDownloadForm) {
        securityDownloadForm.addEventListener("submit", function (event) {
            const selectedEvents = document.querySelectorAll(".event-download-check:checked");

            if (selectedEvents.length === 0) {
                event.preventDefault();
                alert("Please select at least one security notification to download.");
            }
        });
    }
});