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

function setupCustomDatePicker() {
    const hiddenInput = document.getElementById("proposed_transfer_date");
    const monthSelect = document.getElementById("transferMonth");
    const daySelect = document.getElementById("transferDay");
    const yearSelect = document.getElementById("transferYear");

    if (!hiddenInput || !monthSelect || !daySelect || !yearSelect) return;

    const monthNames = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December"
    ];

    function populateMonths() {
        monthSelect.innerHTML = `<option value="">Month</option>`;

        monthNames.forEach((month, index) => {
            const option = document.createElement("option");
            option.value = String(index + 1).padStart(2, "0");
            option.textContent = month;
            monthSelect.appendChild(option);
        });
    }

    function populateYears() {
        const currentYear = new Date().getFullYear();
        const startYear = currentYear - 100;

        yearSelect.innerHTML = `<option value="">Year</option>`;

        for (let year = currentYear; year >= startYear; year--) {
            const option = document.createElement("option");
            option.value = String(year);
            option.textContent = String(year);
            yearSelect.appendChild(option);
        }
    }

    function getDaysInMonth(month, year) {
        if (!month || !year) return 31;
        return new Date(Number(year), Number(month), 0).getDate();
    }

    function populateDays() {
        const selectedDay = daySelect.value;
        const selectedMonth = monthSelect.value;
        const selectedYear = yearSelect.value;
        const totalDays = getDaysInMonth(selectedMonth, selectedYear);

        daySelect.innerHTML = `<option value="">Day</option>`;

        for (let day = 1; day <= totalDays; day++) {
            const option = document.createElement("option");
            option.value = String(day).padStart(2, "0");
            option.textContent = String(day);
            daySelect.appendChild(option);
        }

        if (selectedDay && Number(selectedDay) <= totalDays) {
            daySelect.value = selectedDay;
        }
    }

    function updateHiddenDate() {
        const month = monthSelect.value;
        const day = daySelect.value;
        const year = yearSelect.value;

        if (month && day && year) {
            hiddenInput.value = `${year}-${month}-${day}`;
        } else {
            hiddenInput.value = "";
        }
    }

    populateMonths();
    populateYears();
    populateDays();

    monthSelect.addEventListener("change", function () {
        populateDays();
        updateHiddenDate();
    });

    daySelect.addEventListener("change", function () {
        updateHiddenDate();
    });

    yearSelect.addEventListener("change", function () {
        populateDays();
        updateHiddenDate();
    });
}

function resetCustomDatePicker() {
    const hiddenInput = document.getElementById("proposed_transfer_date");
    const monthSelect = document.getElementById("transferMonth");
    const daySelect = document.getElementById("transferDay");
    const yearSelect = document.getElementById("transferYear");

    if (hiddenInput) hiddenInput.value = "";
    if (monthSelect) monthSelect.value = "";
    if (daySelect) daySelect.value = "";
    if (yearSelect) yearSelect.value = "";
}

document.addEventListener("DOMContentLoaded", function () {
    showSection("view");
    setupFileUpload();
    setupCustomDatePicker();
});