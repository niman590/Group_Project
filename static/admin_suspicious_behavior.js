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
        if (!confirmOverlay || !confirmTitle || !confirmMessage || !confirmDetail || !confirmProceed || !confirmIcon) {
            form.submit();
            return;
        }

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
            if (confirmCancel) {
                confirmCancel.focus();
            }
        }, 80);
    }

    function closeSystemConfirm() {
        if (!confirmOverlay || !confirmProceed) return;

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

    function getElement(id) {
        return document.getElementById(id);
    }

    function padTwoDigits(value) {
        return String(value).padStart(2, "0");
    }

    function getMaxDay(month, year) {
        const monthNumber = Number(month);

        if (!monthNumber) return 31;
        if (year) return new Date(Number(year), monthNumber, 0).getDate();
        if ([4, 6, 9, 11].includes(monthNumber)) return 30;
        if (monthNumber === 2) return 29;

        return 31;
    }

    function rebuildDayOptions(dayElement, maxDay) {
        if (!dayElement) return;

        const currentValue = dayElement.value;
        const fragment = document.createDocumentFragment();
        const placeholder = document.createElement("option");

        placeholder.value = "";
        placeholder.textContent = "Day";
        fragment.appendChild(placeholder);

        for (let day = 1; day <= maxDay; day += 1) {
            const option = document.createElement("option");
            option.value = padTwoDigits(day);
            option.textContent = day;
            fragment.appendChild(option);
        }

        dayElement.innerHTML = "";
        dayElement.appendChild(fragment);

        if (currentValue && Number(currentValue) <= maxDay) {
            dayElement.value = currentValue;
        } else {
            dayElement.value = "";
        }
    }

    function refreshDayOptions(monthId, dayId, yearId) {
        const monthElement = getElement(monthId);
        const dayElement = getElement(dayId);
        const yearElement = getElement(yearId);

        if (!monthElement || !dayElement || !yearElement) return;

        const maxDay = getMaxDay(monthElement.value, yearElement.value);
        rebuildDayOptions(dayElement, maxDay);
    }

    function setDateGroupValidity(monthId, dayId, yearId, message) {
        [monthId, dayId, yearId].forEach((id) => {
            const element = getElement(id);
            if (!element) return;

            element.setCustomValidity(message || "");
            element.classList.toggle("is-invalid", Boolean(message));
        });
    }

    function validateDateGroup(monthId, dayId, yearId, label) {
        const monthElement = getElement(monthId);
        const dayElement = getElement(dayId);
        const yearElement = getElement(yearId);

        if (!monthElement || !dayElement || !yearElement) return true;

        const month = monthElement.value;
        const day = dayElement.value;
        const year = yearElement.value;
        const hasAnyValue = Boolean(month || day || year);
        const hasCompleteDate = Boolean(month && day && year);

        if (hasAnyValue && !hasCompleteDate) {
            setDateGroupValidity(monthId, dayId, yearId, `${label} must include month, day, and year.`);
            return false;
        }

        if (hasCompleteDate && Number(day) > getMaxDay(month, year)) {
            setDateGroupValidity(monthId, dayId, yearId, `${label} is not a valid calendar date.`);
            return false;
        }

        setDateGroupValidity(monthId, dayId, yearId, "");
        return true;
    }

    function updateHiddenDate(monthId, dayId, yearId, hiddenId) {
        const monthElement = getElement(monthId);
        const dayElement = getElement(dayId);
        const yearElement = getElement(yearId);
        const hiddenInput = getElement(hiddenId);

        if (!monthElement || !dayElement || !yearElement || !hiddenInput) return;

        const month = monthElement.value;
        const day = dayElement.value;
        const year = yearElement.value;

        hiddenInput.value = month && day && year ? `${year}-${month}-${day}` : "";
    }

    function syncDateGroup(monthId, dayId, yearId, hiddenId, label) {
        refreshDayOptions(monthId, dayId, yearId);

        const isValid = validateDateGroup(monthId, dayId, yearId, label);
        updateHiddenDate(monthId, dayId, yearId, hiddenId);

        return isValid;
    }

    function validateDateRange() {
        const startDate = getElement("start_date");
        const endDate = getElement("end_date");
        const endDay = getElement("end_day");

        if (!startDate || !endDate || !endDay) return true;

        if (startDate.value && endDate.value && startDate.value > endDate.value) {
            endDay.setCustomValidity("End date must be the same as or later than the start date.");
            endDay.classList.add("is-invalid");
            return false;
        }

        if (endDay.validationMessage === "End date must be the same as or later than the start date.") {
            endDay.setCustomValidity("");
            endDay.classList.remove("is-invalid");
        }

        return true;
    }

    function syncAllDateFilters() {
        const startValid = syncDateGroup("start_month", "start_day", "start_year", "start_date", "Start date");
        const endValid = syncDateGroup("end_month", "end_day", "end_year", "end_date", "End date");
        const rangeValid = startValid && endValid ? validateDateRange() : false;

        return startValid && endValid && rangeValid;
    }

    function reportFirstInvalidControl(container) {
        const invalidControl = container ? container.querySelector(":invalid") : document.querySelector(":invalid");

        if (invalidControl && typeof invalidControl.reportValidity === "function") {
            invalidControl.reportValidity();
        }
    }

    function splitDateToDropdowns(dateValue, monthId, dayId, yearId) {
        if (!dateValue) return;

        const parts = dateValue.split("-");
        if (parts.length !== 3) return;

        const yearElement = getElement(yearId);
        const monthElement = getElement(monthId);
        const dayElement = getElement(dayId);

        if (!yearElement || !monthElement || !dayElement) return;

        yearElement.value = parts[0];
        monthElement.value = parts[1];
        refreshDayOptions(monthId, dayId, yearId);
        dayElement.value = parts[2];
    }

    function syncDownloadFilters(downloadForm) {
        if (!downloadForm) return true;
        if (!syncAllDateFilters()) return false;

        const pageSeverity = getElement("severity");
        const pageStatus = getElement("status");
        const pageRuleName = getElement("rule_name");
        const pageStartDate = getElement("start_date");
        const pageEndDate = getElement("end_date");

        const downloadSeverity = downloadForm.querySelector("input[name='severity']");
        const downloadStatus = downloadForm.querySelector("input[name='status']");
        const downloadRuleName = downloadForm.querySelector("input[name='rule_name']");
        const downloadStartDate = downloadForm.querySelector("input[name='start_date']");
        const downloadEndDate = downloadForm.querySelector("input[name='end_date']");

        if (downloadSeverity && pageSeverity) downloadSeverity.value = pageSeverity.value;
        if (downloadStatus && pageStatus) downloadStatus.value = pageStatus.value;
        if (downloadRuleName && pageRuleName) downloadRuleName.value = pageRuleName.value;
        if (downloadStartDate && pageStartDate) downloadStartDate.value = pageStartDate.value;
        if (downloadEndDate && pageEndDate) downloadEndDate.value = pageEndDate.value;

        return true;
    }

    const dates = window.securityFilterDates || {
        startDate: "",
        endDate: ""
    };

    splitDateToDropdowns(dates.startDate, "start_month", "start_day", "start_year");
    splitDateToDropdowns(dates.endDate, "end_month", "end_day", "end_year");
    syncAllDateFilters();

    ["start_month", "start_day", "start_year"].forEach((id) => {
        const element = getElement(id);
        if (!element) return;

        element.addEventListener("change", function () {
            syncDateGroup("start_month", "start_day", "start_year", "start_date", "Start date");
            validateDateRange();
        });
    });

    ["end_month", "end_day", "end_year"].forEach((id) => {
        const element = getElement(id);
        if (!element) return;

        element.addEventListener("change", function () {
            syncDateGroup("end_month", "end_day", "end_year", "end_date", "End date");
            validateDateRange();
        });
    });

    const securityFilterForm = getElement("securityFilterForm");

    if (securityFilterForm) {
        securityFilterForm.addEventListener("submit", function (event) {
            if (!syncAllDateFilters()) {
                event.preventDefault();
                reportFirstInvalidControl(securityFilterForm);
            }
        });
    }

    const securityDownloadForm = getElement("securityDownloadForm");

    if (securityDownloadForm) {
        securityDownloadForm.addEventListener("submit", function (event) {
            if (!syncDownloadFilters(securityDownloadForm)) {
                event.preventDefault();
                reportFirstInvalidControl(document);
                return;
            }

            const downloadButton = securityDownloadForm.querySelector("button[type='submit']");
            if (!downloadButton) return;

            downloadButton.disabled = true;
            downloadButton.dataset.originalText = downloadButton.innerHTML;
            downloadButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparing PDF...';

            setTimeout(() => {
                downloadButton.disabled = false;
                downloadButton.innerHTML =
                    downloadButton.dataset.originalText ||
                    '<i class="fa-solid fa-file-pdf"></i> Download Filtered PDF';
            }, 2500);
        });
    }
});