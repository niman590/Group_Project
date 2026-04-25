function showSection(type) {
    const viewSection = document.getElementById("view-section");
    const updateSection = document.getElementById("update-section");
    const viewTab = document.getElementById("view-tab");
    const updateTab = document.getElementById("update-tab");

    viewSection.classList.add("hidden");
    updateSection.classList.add("hidden");
    viewTab.classList.remove("active");
    updateTab.classList.remove("active");

    if (type === "view") {
        viewSection.classList.remove("hidden");
        viewTab.classList.add("active");
    } else {
        updateSection.classList.remove("hidden");
        updateTab.classList.add("active");
    }
}

function escapeHtml(value) {
    if (value === null || value === undefined) return "-";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderLoadingState(title, message) {
    return `
        <div class="empty-state-card loading-card">
            <div class="empty-state-icon">
                <i class="fa-solid fa-spinner fa-spin"></i>
            </div>
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

function renderEmptyState(title, message, icon = "fa-folder-open") {
    return `
        <div class="empty-state-card">
            <div class="empty-state-icon">
                <i class="fa-solid ${icon}"></i>
            </div>
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

async function fetchTransactionHistory() {
    const deedInput = document.getElementById("view_deed_number");
    const resultDiv = document.getElementById("history-result");
    const deedNumber = deedInput.value.trim();

    if (!deedNumber) {
        resultDiv.innerHTML = `<div class="error-msg">Please enter a deed number.</div>`;
        deedInput.focus();
        return;
    }

    resultDiv.innerHTML = renderLoadingState(
        "Searching history...",
        "Please wait while we retrieve ownership records."
    );

    try {
        const response = await fetch("/get-transaction-history", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ deed_number: deedNumber })
        });

        const data = await response.json();

        if (data.error) {
            resultDiv.innerHTML = `<div class="error-msg">${escapeHtml(data.error)}</div>`;
            return;
        }

        let html = `
            <div class="history-overview">
                <div class="overview-card">
                    <span>Deed Number</span>
                    <strong>${escapeHtml(data.deed_number)}</strong>
                </div>

                <div class="overview-card">
                    <span>Current Owner</span>
                    <p>${escapeHtml(data.current_owner_name)}</p>
                </div>

                <div class="overview-card">
                    <span>Property Address</span>
                    <p>${escapeHtml(data.property_address)}</p>
                </div>

                <div class="overview-card">
                    <span>Location</span>
                    <p>${escapeHtml(data.location)}</p>
                </div>
            </div>
        `;

        if (!Array.isArray(data.history) || data.history.length === 0) {
            html += renderEmptyState(
                "No ownership history found",
                "No transaction records were returned for this deed number.",
                "fa-circle-info"
            );
            resultDiv.innerHTML = html;
            return;
        }

        html += `<h3 class="timeline-title">Ownership Timeline</h3>`;
        html += `<div class="timeline">`;

        data.history.forEach((item) => {
            html += `
                <div class="timeline-item">
                    <div class="timeline-top">
                        <span class="timeline-order">Order ${escapeHtml(item.ownership_order)}</span>
                        <span class="timeline-type">${escapeHtml(item.transaction_type || "-")}</span>
                    </div>

                    <div class="timeline-grid">
                        <div class="timeline-field">
                            <span>Owner Name</span>
                            <strong>${escapeHtml(item.owner_name)}</strong>
                        </div>

                        <div class="timeline-field">
                            <span>Transfer Date</span>
                            <strong>${escapeHtml(item.transfer_date)}</strong>
                        </div>

                        <div class="timeline-field">
                            <span>NIC</span>
                            <strong>${escapeHtml(item.owner_nic || "-")}</strong>
                        </div>

                        <div class="timeline-field">
                            <span>Phone</span>
                            <strong>${escapeHtml(item.owner_phone || "-")}</strong>
                        </div>

                        <div class="timeline-field full-timeline-field">
                            <span>Address</span>
                            <strong>${escapeHtml(item.owner_address || "-")}</strong>
                        </div>
                    </div>
                </div>
            `;
        });

        html += `</div>`;
        resultDiv.innerHTML = html;

    } catch (err) {
        resultDiv.innerHTML = `<div class="error-msg">Something went wrong while fetching transaction history.</div>`;
    }
}

async function submitUpdateRequest() {
    const form = document.getElementById("updateForm");
    const resultDiv = document.getElementById("update-result");
    const submitBtn = document.querySelector(".submit-btn");
    const formData = new FormData(form);

    const deedNumber = String(formData.get("deed_number") || "").trim();
    const ownerName = String(formData.get("proposed_owner_name") || "").trim();
    const transferDate = String(formData.get("proposed_transfer_date") || "").trim();
    const proofDocument = formData.get("proof_document");

    if (!deedNumber) {
        resultDiv.innerHTML = `<div class="error-msg">Deed number is required.</div>`;
        return;
    }

    if (!ownerName) {
        resultDiv.innerHTML = `<div class="error-msg">Owner name is required.</div>`;
        return;
    }

    if (!transferDate) {
        resultDiv.innerHTML = `<div class="error-msg">Transfer date is required.</div>`;
        return;
    }

    if (!proofDocument || !proofDocument.name) {
        resultDiv.innerHTML = `<div class="error-msg">Please upload a proof document.</div>`;
        return;
    }

    resultDiv.innerHTML = renderLoadingState(
        "Submitting request...",
        "Please wait while we send your request for admin review."
    );

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>Submitting...</span>`;
    }

    try {
        const response = await fetch("/request-transaction-history-update", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            resultDiv.innerHTML = `<div class="error-msg">${escapeHtml(data.error)}</div>`;
            return;
        }

        resultDiv.innerHTML = `
            <div class="success-msg">
                <i class="fa-solid fa-circle-check"></i>
                <span>${escapeHtml(data.message || "Request submitted successfully.")}</span>
            </div>
        `;

        form.reset();
        resetFileUpload();
        resetCustomDatePicker();

    } catch (err) {
        resultDiv.innerHTML = `<div class="error-msg">Something went wrong while submitting the request.</div>`;
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fa-solid fa-paper-plane"></i><span>Submit Request</span>`;
        }
    }
}

function resetFileUpload() {
    const fileBox = document.getElementById("customFileBox");
    const fileName = document.getElementById("file-name");
    const fileTitle = document.getElementById("file-title");

    if (fileBox) fileBox.classList.remove("active", "drag-over");
    if (fileName) fileName.textContent = "No file selected";
    if (fileTitle) fileTitle.textContent = "Drag & drop proof document here";
}

function setupFileUpload() {
    const fileInput = document.getElementById("proof_document");
    const fileBox = document.getElementById("customFileBox");
    const fileName = document.getElementById("file-name");
    const fileTitle = document.getElementById("file-title");

    if (!fileInput || !fileBox || !fileName || !fileTitle) return;

    fileInput.addEventListener("change", function () {
        if (this.files && this.files.length > 0) {
            fileName.textContent = this.files[0].name;
            fileTitle.textContent = "Proof document selected";
            fileBox.classList.add("active");
        } else {
            resetFileUpload();
        }
    });

    fileBox.addEventListener("dragover", function (event) {
        event.preventDefault();
        fileBox.classList.add("drag-over");
    });

    fileBox.addEventListener("dragleave", function () {
        fileBox.classList.remove("drag-over");
    });

    fileBox.addEventListener("drop", function (event) {
        event.preventDefault();
        fileBox.classList.remove("drag-over");

        if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
            fileInput.files = event.dataTransfer.files;
            fileName.textContent = event.dataTransfer.files[0].name;
            fileTitle.textContent = "Proof document selected";
            fileBox.classList.add("active");
        }
    });
}

let customDatePickerState = {
    currentDate: new Date(),
    selectedDate: null
};

function setupCustomDatePicker() {
    const hiddenInput = document.getElementById("proposed_transfer_date");
    const button = document.getElementById("datePickerButton");
    const popup = document.getElementById("datePopup");
    const selectedText = document.getElementById("selectedDateText");
    const monthYear = document.getElementById("calendarMonthYear");
    const daysContainer = document.getElementById("calendarDays");
    const prevBtn = document.getElementById("prevMonth");
    const nextBtn = document.getElementById("nextMonth");
    const clearBtn = document.getElementById("clearDate");
    const todayBtn = document.getElementById("todayDate");
    const picker = document.getElementById("customDatePicker");

    if (!hiddenInput || !button || !popup || !daysContainer || !picker) return;

    function formatDateForInput(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function formatDateForDisplay(date) {
        return date.toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric"
        });
    }

    function isSameDate(dateOne, dateTwo) {
        return (
            dateOne &&
            dateTwo &&
            dateOne.getDate() === dateTwo.getDate() &&
            dateOne.getMonth() === dateTwo.getMonth() &&
            dateOne.getFullYear() === dateTwo.getFullYear()
        );
    }

    function renderCalendar() {
        daysContainer.innerHTML = "";

        const year = customDatePickerState.currentDate.getFullYear();
        const month = customDatePickerState.currentDate.getMonth();

        monthYear.textContent = customDatePickerState.currentDate.toLocaleDateString("en-US", {
            month: "long",
            year: "numeric"
        });

        const firstDay = new Date(year, month, 1).getDay();
        const totalDays = new Date(year, month + 1, 0).getDate();
        const today = new Date();

        for (let i = 0; i < firstDay; i++) {
            const empty = document.createElement("span");
            empty.className = "date-empty";
            daysContainer.appendChild(empty);
        }

        for (let day = 1; day <= totalDays; day++) {
            const dayBtn = document.createElement("button");
            dayBtn.type = "button";
            dayBtn.textContent = day;

            const dateObj = new Date(year, month, day);

            if (isSameDate(dateObj, today)) {
                dayBtn.classList.add("today");
            }

            if (isSameDate(dateObj, customDatePickerState.selectedDate)) {
                dayBtn.classList.add("selected");
            }

            dayBtn.addEventListener("click", function () {
                customDatePickerState.selectedDate = dateObj;
                hiddenInput.value = formatDateForInput(dateObj);
                selectedText.textContent = formatDateForDisplay(dateObj);
                popup.classList.add("hidden");
                button.classList.add("date-selected");
                renderCalendar();
            });

            daysContainer.appendChild(dayBtn);
        }
    }

    button.addEventListener("click", function () {
        popup.classList.toggle("hidden");
        renderCalendar();
    });

    prevBtn.addEventListener("click", function () {
        customDatePickerState.currentDate.setMonth(customDatePickerState.currentDate.getMonth() - 1);
        renderCalendar();
    });

    nextBtn.addEventListener("click", function () {
        customDatePickerState.currentDate.setMonth(customDatePickerState.currentDate.getMonth() + 1);
        renderCalendar();
    });

    clearBtn.addEventListener("click", function () {
        customDatePickerState.selectedDate = null;
        hiddenInput.value = "";
        selectedText.textContent = "Select transfer date";
        button.classList.remove("date-selected");
        popup.classList.add("hidden");
        renderCalendar();
    });

    todayBtn.addEventListener("click", function () {
        const today = new Date();
        customDatePickerState.selectedDate = today;
        customDatePickerState.currentDate = new Date(today.getFullYear(), today.getMonth(), 1);
        hiddenInput.value = formatDateForInput(today);
        selectedText.textContent = formatDateForDisplay(today);
        button.classList.add("date-selected");
        popup.classList.add("hidden");
        renderCalendar();
    });

    document.addEventListener("click", function (event) {
        if (!picker.contains(event.target)) {
            popup.classList.add("hidden");
        }
    });

    renderCalendar();
}

function resetCustomDatePicker() {
    const hiddenInput = document.getElementById("proposed_transfer_date");
    const selectedText = document.getElementById("selectedDateText");
    const button = document.getElementById("datePickerButton");
    const popup = document.getElementById("datePopup");

    customDatePickerState.currentDate = new Date();
    customDatePickerState.selectedDate = null;

    if (hiddenInput) hiddenInput.value = "";
    if (selectedText) selectedText.textContent = "Select transfer date";
    if (button) button.classList.remove("date-selected");
    if (popup) popup.classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", function () {
    showSection("view");
    setupFileUpload();
    setupCustomDatePicker();
});